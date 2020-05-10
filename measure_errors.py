#!/usr/bin/env python
"""Script to measure the errors from a transcription system in order to create
a degraded MIDI dataset with the given proportions of degradations."""
import argparse
import glob
import os
import pandas as pd
import pickle
import numpy as np
import warnings

import pretty_midi

from mdtk import degradations, midi, data_structures, formatters
from mdtk.degradations import (MIN_PITCH_DEFAULT, MAX_PITCH_DEFAULT,
                               DEGRADATIONS, MIN_SHIFT_DEFAULT)
from mdtk.data_structures import NOTE_DF_SORT_ORDER

FILE_TYPES = ['mid', 'pkl', 'csv']



def get_df_excerpt(note_df, start_time, end_time):
    """
    Return an excerpt of the given note_df, with notes cut at the given
    start and end times.
    
    Parameters
    ----------
    note_df : pd.DataFrame
        The note_df we want to take an excerpt of.
        
    start_time : int
        The start time for the returned excerpt, in ms, inclusive. Notes
        entirely before this time will be dropped. Notes which onset before
        this time but continue after it will have their onset shifted to
        this time.
        
    end_time : int
        The end time for the returned excerpt, in ms, exclusive. Notes
        entirely after this time will be dropped. Notes which onset before
        this time but continue after it will have their offset shifted to
        this time. None to enforce no end time.
    
    Returns
    -------
    note_df : pd.DataFrame
        An excerpt of the notes from the given note_df, within the given
        two times.
    """
    # Make copy so as not to change original values
    note_df = note_df.copy()
    
    # Move onsets of notes which lie before start (and finish after start)
    need_to_shift = ((note_df.onset < start_time) &
                     (note_df.onset + note_df.dur > start_time))
    shift_amt = start_time - note_df.loc[need_to_shift, 'onset']
    note_df.loc[need_to_shift, 'onset'] = start_time
    note_df.loc[need_to_shift, 'dur'] -= shift_amt
    
    # Shorten notes which go past end time
    if end_time is not None:
        need_to_shorten = ((note_df.onset < end_time) &
                           (note_df.onset + note_df.dur > end_time))
        note_df.loc[need_to_shorten, 'dur'] = (
            end_time - note_df.loc[need_to_shorten, 'onset']
        )
    
    # Drop notes which lie outside of bounds
    to_keep = note_df.onset >= start_time
    if end_time is not None:
        to_keep &= note_df.onset < end_time
    note_df = note_df.loc[to_keep]
    return note_df


def load_file(filename, pr_min_pitch=MIN_PITCH_DEFAULT,
              pr_max_pitch=MAX_PITCH_DEFAULT, pr_time_increment=40):
    """
    Load the given filename into a pandas dataframe.

    Parameters
    ----------
    filename : string
        The file to load into a dataframe.

    pr_min_pitch : int
        The minimum pitch for any piano roll, inclusive.

    pr_max_pitch : int
        The maximum pitch for any piano roll, inclusive.

    pr_time_increment : int
        The length of each frame of any piano roll.

    Return
    ------
    df : pandas dataframe
        A pandas dataframe representing the music from the given file.
    """
    ext = os.path.splitext(os.path.basename(filename))[1]

    if ext == '.mid':
        return midi.midi_to_df(filename)

    if ext == '.csv':
        return pd.read_csv(filename, names=['onset', 'track', 'pitch', 'dur'])

    if ext == '.pkl':
        with open(filename, 'rb') as file:
            pkl = pickle.load(file)

        piano_roll = pkl['piano_roll']

        if piano_roll.shape[1] == (pr_min_pitch - pr_max_pitch + 1):
            # Normal piano roll only -- no onsets
            note_pr = piano_roll.astype(int)
            onset_pr = ((np.roll(note_pr, 1, axis=0) - note_pr) == -1)
            onset_pr[0] = note_pr[0]
            onset_pr = onset_pr.astype(int)

        elif piano_roll.shape[1] == 2 * (pr_min_pitch - pr_max_pitch + 1):
            # Piano roll with onsets
            note_pr = piano_roll[:, :piano_roll.shape[1] / 2].astype(int)
            onset_pr = piano_roll[:, piano_roll.shape[1] / 2:].astype(int)

        else:
            raise ValueError("Piano roll dimension 2 size ("
                             f"{piano_roll.shape[1]}) must be equal to 1 or 2"
                             f" times the given pitch range [{pr_min_pitch} - "
                             f"{pr_max_pitch}] = "
                             f"{pr_min_pitch - pr_max_pitch + 1}")
            
        piano_roll = np.vstack((note_pr, onset_pr))
        return formatters.double_pianoroll_to_df(
            piano_roll, min_pitch=pr_min_pitch, max_pitch=pr_max_pitch,
            time_increment=pr_time_increment)

    raise NotImplementedError(f'Extension {ext} not supported.')



def get_note_degs(gt_note, trans_note):
    """
    Get the count of each degradation given a ground truth note and a
    transcribed note.
    
    Parameters
    ----------
    gt_note : dict
        The ground truth note, with integer fields onset, pitch, track,
        and dur.

    trans_note : dict
        The corresponding transcribed note, with integer fields onset,
        pitch, track, and dur.

    Returns
    -------
    deg_counts : np.array(float)
        The count of each degradation between the notes, for the set
        of degradations which lead to the smallest total number of
        degradations. If multiple sets of degradations lead to the
        ground truth in the same total number of degradations, the mean
        of those counts is returned. Indices are in order of
        mdtk.degradations.DEGRADATIONS.
    """
    deg_counts = np.zeros(len(DEGRADATIONS))

    # Pitch shift
    if gt_note['pitch'] != trans_note['pitch']:
        deg_counts[list(DEGRADATIONS).index('pitch_shift')] = 1

    # Time shift
    if abs(gt_note['dur'] - trans_note['dur']) < MIN_SHIFT_DEFAULT:
        if abs(gt_note['onset'] - trans_note['onset']) < MIN_SHIFT_DEFAULT:
            return deg_counts
        deg_counts[list(DEGRADATIONS).index('time_shift')] = 1
        return deg_counts

    # Onset shift
    if abs(gt_note['onset'] - trans_note['onset']) >= MIN_SHIFT_DEFAULT:
        deg_counts[list(DEGRADATIONS).index('onset_shift')] = 1

    # Offset shift
    gt_offset = gt_note['onset'] + gt_note['dur']
    trans_offset = trans_note['onset'] + trans_note['dur']
    if abs(gt_offset - trans_offset) >= MIN_SHIFT_DEFAULT:
        deg_counts[list(DEGRADATIONS).index('offset_shift')] = 1

    return deg_counts



def get_excerpt_degs(gt_excerpt, trans_excerpt):
    """
    Get the count of each degradation given a ground truth excerpt and a
    transcribed excerpt.

    Parameters
    ----------
    gt_excerpt : pd.DataFrame
        The ground truth data frame.

    trans_excerpt : pd.DataFrame
        The corresponding transcribed dataframe.

    Returns
    -------
    degs : np.array(float)
        The estimated count of each degradation in this transcription, in the
        order given by mdtk.degradations.DEGRADATIONS.
    """
    deg_counts = np.zeros(len(DEGRADATIONS))
    
    # Case 1: gt is empty
    if len(gt_excerpt) == 0:
        deg_counts[list(DEGRADATIONS).index('add_note')] = len(trans_excerpt)
        return deg_counts

    # Case 2: transcription is empty
    if len(trans_excerpt) == 0:
        deg_counts[list(DEGRADATIONS).index('remove_note')] = len(gt_excerpt)
        return deg_counts
    
    # TODO: Degredation estimation
    
    return deg_counts



def get_proportions(gt, trans, trans_start=0, trans_end=None, length=5000,
                    min_notes=10):
    """
    Get the proportions of each degradation given a ground truth file and its
    transcription.
    
    Parameters
    ----------
    gt : string
        The filename of a ground truth musical score.
        
    trans : string
        The filename of a transciption of the given ground truth.
        
    trans_start : int
        The starting time of the transcription, in ms.
        
    trans_end : int
        The ending time of the transcription, in ms.
        
    length : int
        The length of the excerpts to grab in ms (plus sustains).
        
    min_notes : int
        The minimum number of notes required for an excerpt to be valid.
        
    Returns
    -------
    proportions : list(float)
        The rough proportion of excerpts from the ground truth with each
        degradation present in the transcription, in the order given by
        mdtk.degradations.DEGRADATIONS.
        
    clean : float
        The rough proportion of excerpts from the ground truth whose
        transcription is correct.
    """
    num_excerpts = 0
    deg_counts = np.zeros(len(DEGRADATIONS))
    clean_count = 0

    gt_df = load_file(gt)
    trans_df = load_file(trans)
    
    # Enforce transcription bounds
    gt_df = get_df_excerpt(gt_df, trans_start, trans_end)
    if trans_start != 0:
        gt_df.onset -= trans_start
    
    end_time = max((gt_df.onset + gt_df.dur).max(),
                   (trans_df.onset + trans_df.dur).max())
    # Take each excerpt from time 0 until the end
    for excerpt_start in range(0, end_time, length):
        excerpt_end = min(excerpt_start + length, end_time)
        gt_excerpt = get_df_excerpt(gt_df, excerpt_start, excerpt_end)
        trans_excerpt = get_df_excerpt(trans_df, excerpt_start, excerpt_end)

        # Check for validity
        if len(gt_excerpt) < min_notes and len(trans_excerpt) < min_notes:
            warnings.warn(f'Skipping excerpt {gt} for too few notes. '
                          f'Time range = [{excerpt_start}, {excerpt_end}). '
                          f'Try lowering the minimum note count --min-notes '
                          f'(currently {min_notes}), or '
                          'ignore this if it is just due to a song length '
                          'not being divisible by the --excerpt-length '
                          f'(currently {length}).')
            continue

        num_excerpts += 1
        excerpt_degs = get_excerpt_degs(gt_excerpt, trans_excerpt)
        deg_counts += degs
        if np.sum(excerpt_degs) == 0:
            clean_count += 1

    # Divide number of errors by the number of possible excerpts
    if num_excerpts - clean_count == 0:
        proportions = deg_counts
    else:
        proportions = deg_counts / (num_excerpts - clean_count)
    clean = clean_count / num_excerpts if num_excerpts > 0 else 0
    return proportions, clean



def parse_args(args_input=None):
    parser = argparse.ArgumentParser(description="Measure errors from a "
                                     "transcription error in order to make "
                                     "a degraded MIDI dataset with the measure"
                                     " proportion of each degration.")
    
    parser.add_argument("--json", help="The file to write the degradation config"
                        " json data out to.", default="config.json")
    
    parser.add_argument("--gt", help="The directory which contains the ground "
                        "truth musical scores or piano rolls.", required=True)
    parser.add_argument("--gt_ext", choices=FILE_TYPES, default=None,
                        help="Restrict the file type for the ground truths.")
    
    parser.add_argument("--trans", help="The directory which contains the "
                        "transcriptions.", required=True)
    parser.add_argument("--trans_ext", choices=FILE_TYPES, default=None,
                        help="Restrict the file type for the transcriptions.")
    
    # Pianoroll specific args
    parser.add_argument("--pr-min-pitch", type=int, default=21,
                        help="Minimum pianoroll pitch.")
    parser.add_argument("--pr-max-pitch", type=int, default=108,
                        help="Maximum pianoroll pitch.")
    
    # Transcription doesn't have same time basis as ground truth
    parser.add_argument("--trans_start", type=int, default=0, help="What time"
                        " the transcription starts, in ms. Notes before this "
                        "in the gt will be ignored, and all transcribed notes "
                        "will be shifted forward by this amount.")
    parser.add_argument("--trans_end", type=int, default=None, help="What time"
                        "the transcription ends, in ms (if any). Notes after "
                        "this in the gt will be ignored, and notes still on "
                        "will be cut at this time.")
    
    # Excerpt arguments
    parser.add_argument('--excerpt-length', metavar='ms', type=int,
                        help='The length of the excerpt (in ms) to take from '
                        'each piece. The excerpt will start on a note onset '
                        'and include all notes whose onset lies within this '
                        'number of ms after the first note.', default=5000)
    parser.add_argument('--min-notes', metavar='N', type=int, default=10,
                        help='The minimum number of notes required for an '
                        'excerpt to be valid.')
    args = parser.parse_args(args=args_input)
    return args



if __name__ == '__main__':
    args = parse_args()
    
    # Get allowed file extensions
    trans_ext = [args.trans_ext] if args.trans_ext is not None else FILE_TYPES
    gt_ext = [args.gt_ext] if args.gt_ext is not None else FILE_TYPES
    
    trans = []
    for ext in trans_ext:
        trans.extend(glob.glob(os.path.join(args.trans, '*.' + ext)))
    
    proportion = np.zeros((0, len(DEGRADATIONS)))
    clean_prop = []
    
    for file in trans:
        basename = os.path.splitext(os.path.basename(file))[0]
        
        # Find gt file
        gt_list = []
        for ext in gt_ext:
            gt_list.extend(glob.glob(os.path.join(args.gt, basename + '.' + ext)))
            
        if len(gt_list) == 0:
            warnings.warn(f'No ground truth found for transcription {file}. Check'
                          ' that the file extension --gt_ext is correct (or not '
                          'given), and the dir --gt is correct. Searched for file'
                          f' {basename}.{gt_ext} in dir {args.gt}.')
            continue
        elif len(gt_list) > 1:
            warnings.warn(f'Multiple ground truths found for transcription {file}:'
                          f'{gt_list}. Defaulting to the first one. Try narrowing '
                          'down extensions with --gt_ext.')
        gt = gt_list[0]
        
        # TODO: Also get some parameters?
        prop, clean = get_proportions(gt, file, trans_start=args.trans_start,
                                      trans_end=args.trans_end,
                                      length=args.excerpt_length,
                                      min_notes=args.min_notes)
        proportion = np.vstack((proportion, prop))
        clean_prop.append(clean)
        
    proportion = np.mean(proportion, axis=0)
    clean = np.mean(clean_prop)
    
    # TODO: Write out to json file
    
    