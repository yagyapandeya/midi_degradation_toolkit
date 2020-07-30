"""Code to interact with MIDI files, including parsing and converting them
to csvs."""
import os
import warnings
from glob import glob

import pandas as pd
from tqdm import tqdm

import pretty_midi

from mdtk.data_structures import NOTE_DF_SORT_ORDER, check_note_df



COLNAMES = NOTE_DF_SORT_ORDER



def midi_dir_to_csv(midi_dir_path, csv_dir_path, recursive=False):
    """
    Convert an entire directory of MIDI files into csvs in another directory.
    This searches the given MIDI path for any files with the extension 'mid'.
    It will create any necessary directories for the csv files, and will
    create one csv per MIDI file, where the 'mid' extension is replaced with
    'csv'.

    Parameters
    ----------
    midi_dir_path : string
        The path of a directory which contains any number of MIDI files with
        extension 'mid'. The directory is not searched recursively, and any
        files with a different extension are ignored.

    csv_dir_path : string
        The path of the directory to write out each csv to. If it does not
        exist, it will be created.

    recursive : boolean
        If True, search the given midi dir recursively.
    """
    if recursive:
        dir_prefix_len = len(midi_dir_path) + 1
        midi_dir_path = os.path.join(midi_dir_path, '**')
    for midi_path in tqdm(glob(os.path.join(midi_dir_path, '*.mid')),
                          desc='Converting midi from '
                          f'{os.path.basename(midi_dir_path)} to csv '
                          f'at {os.path.basename(csv_dir_path)}: '):
        if recursive:
            csv_path = os.path.join(
                csv_dir_path,
                os.path.dirname(midi_path[dir_prefix_len:]),
                os.path.basename(midi_path[:-3] + 'csv')
            )
        else:
            csv_path = os.path.join(
                csv_dir_path,
                os.path.basename(midi_path[:-3] + 'csv')
            )
        midi_to_csv(midi_path, csv_path)


def midi_to_csv(midi_path, csv_path):
    """
    Convert a MIDI file into a csv file.

    Parameters
    ----------
    midi_path : string
        The filename of the MIDI file to parse.

    csv_path : string
        The filename of the csv to write out to. Any nested directories will be
        created by df_to_csv(df, csv_path).
    """
    df_to_csv(midi_to_df(midi_path), csv_path)


def midi_to_df(midi_path, warn=False):
    """
    Get the data from a MIDI file and load it into a pandas DataFrame.

    Parameters
    ----------
    midi_path : string
        The filename of the MIDI file to parse.

    Returns
    -------
    df : DataFrame
        A pandas DataFrame containing the notes parsed from the given MIDI
        file. There will be 4 columns:
            onset: Onset time of the note, in milliseconds.
            track: The track number of the instrument the note is from.
            pitch: The MIDI pitch number for the note.
            dur: The duration of the note (offset - onset), in milliseconds.
        Sorting will be first by onset, then track, then pitch, then duration.
    """
    try:
        midi = pretty_midi.PrettyMIDI(midi_path)
    except:
        warnings.warn(f'Error parsing midi file {midi_path}. Skipping.')
        return None

    notes = []
    for index, instrument in enumerate(midi.instruments):
        for note in instrument.notes:
            notes.append({'onset': int(round(note.start * 1000)),
                          'track': index,
                          'pitch': note.pitch,
                          'dur': int(round(note.end * 1000) -
                                     round(note.start * 1000))})
    if len(notes) == 0:
        warnings.warn(f'WARNING: the midi file located at {midi_path} is '
                       'empty. Returning None.', category=UserWarning)
        return None
    df = pd.DataFrame(notes)[COLNAMES]
    df = df.sort_values(COLNAMES)
    df = df.reset_index(drop=True)
    if warn:
        check_note_df(df)
    return df


def df_to_csv(df, csv_path):
    """
    Print the data from the given pandas DataFrame into a csv in the correct
    format.

    Parameters
    ----------
    df : DataFrame
        The DataFrame to write out to a csv. It should be in the format returned
        by midi_to_df(midi_path), with 4 columns:
            onset: Onset time of the note, in milliseconds
            track: The track number of the instrument the note is from.
            pitch: The MIDI pitch number for the note.
            dur: The duration of the note (offset - onset), in milliseconds.

    csv_path : string
        The filename of the csv to which to print the data. No header or index
        will be printed, and the rows will be printed in the current order of the
        DataFrame. Any nested directories will be created.
    """
    if df is None or len(df) == 0:
        return None
    if os.path.split(csv_path)[0]:
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    # Enforce column order
    df[COLNAMES].to_csv(csv_path, index=None, header=False)


def df_to_midi(df, midi_path, existing_midi_path=None, excerpt_start=0,
               excerpt_length=float('Inf')):
    """
    Write the notes of a DataFrame out to a MIDI file.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame containing an excerpt to write out.

    midi_path : string
        The filename to write out to.

    existing_midi_path : string
        The path to an existing MIDI file. If given, non-note events will be
        copied from this file to the newly created MIDI file, and the df's
        tracks will reference the existing MIDI file's instruments in the order
        given by the existing MIDI file's instrument list.

    excerpt_start : int
        The time (in ms) to align df's time 0 with in the new MIDI file. This
        value cannot be negative. If existing_midi_path is given, any notes
        whose onset is before this time are copied into the new MIDI file.

    excerpt_length : int
        Used only if existing_midi_path is given, this represents the length
        of the excerpt in ms. Any notes whose onset is after excerpt_start +
        excerpt_length are copied into the new MIDI file.
    """
    assert excerpt_start >= 0, "excerpt_start must not be negative"
    excerpt_start_secs = excerpt_start / 1000

    midi = pretty_midi.PrettyMIDI()
    instruments = [None] * (df.track.max() + 1)

    # Copy data from existing MIDI file
    if existing_midi_path is not None:
        existing_midi = pretty_midi.PrettyMIDI(existing_midi_path)
        excerpt_end_secs = excerpt_start_secs + excerpt_length / 1000

        # Copy time, key, and lyric events
        midi.key_signature_changes = existing_midi.key_signature_changes
        midi.time_signature_changes = existing_midi.time_signature_changes
        midi.lyrics = existing_midi.lyrics

        # Write to instrument tracks in order parsed by pretty_midi
        for i, instrument in enumerate(existing_midi.instruments):
            instruments[i] = pretty_midi.Instrument(
                instrument.program, is_drum=instrument.is_drum,
                name=instrument.name
            )

            # Copy all non-note events
            instruments[i].pitch_bends = instrument.pitch_bends
            instruments[i].control_changes = instrument.control_changes

            # Copy all valid notes
            instruments[i].notes = [
                note for note in instrument.notes if (
                    note.start < excerpt_start_secs or
                    note.start >= excerpt_end_secs
                )
            ]

    # Create tracks for those not covered by the existing MIDI file
    for track in df.track.unique():
        if instruments[track] is not None:
            continue

        # Naively assume MIDI program number is df.track
        instrument = pretty_midi.Instrument(track)
        instruments[track] = instrument

    # Add all instruments to the midi object
    midi.instruments = [
        instrument for instrument in instruments if instrument is not None
    ]

    # Compute start and end time of notes in seconds as pretty_midi expects
    df.loc[:, 'start'] = df.onset / 1000 + excerpt_start_secs
    df.loc[:, 'end'] = df.start + df.dur / 1000

    # Add df notes to midi object
    for note in df.itertuples():
        midi_note = pretty_midi.Note(velocity=100, pitch=note.pitch,
                                     start=note.start, end=note.end)
        instruments[int(note.track)].notes.append(midi_note)

    df.drop(columns=['start', 'end'], axis=1, inplace=True)
    midi.write(midi_path)
