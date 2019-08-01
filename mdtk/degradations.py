"""Code to perform the degradations i.e. edits to the midi data"""
from mdtk.data_structures import Composition


def get_degradations():
    """
    Get a dict mapping the name of each degradation to its function pointer.
    
    Returns
    -------
    degradations : dict(string -> func)
        A dict containing the name of each degradation mapped to a pointer to
        the method which performs that degradation.
    """
    return {'pitch_shift': pitch_shift,
            'time_shift': time_shift,
            'onset_shift': onset_shift,
            'offset_shift': offset_shift,
            'remove_note': remove_note,
            'add_note': add_note}



def pitch_shift(excerpt, rand, params):
    """
    Shift the pitch of one note from the given excerpt.
    
    Parameters
    ----------
    excerpt : Composition
        A Composition object of an excerpt from a piece of music.
        
    rand : numpy.random
        A seeded numpy random object.
        
    params : dict
        A dictionary containing parameters for the pitch shift. All used
        parameters keys will begin with 'pitch_shift_'. They include:
            min_pitch : int
                The minimum pitch to which a note may be shifted.
                Defaults to 0.
            max_pitch : int
                One greater than the maximum pitch to which a note may be
                shifted. Defaults to 88.
            
    Returns
    -------
    degraded : Composition
        A copy of the given excerpt, with the pitch of one note changed.
    """
    min_pitch = (0 if 'pitch_shift_min_pitch' not in params
                 else params['pitch_shift_min_pitch'])
    max_pitch = (88 if 'pitch_shift_max_pitch' not in params
                 else params['pitch_shift_max_pitch'])
    
    degraded = excerpt.copy()
    
    # Sample a random note
    note_index = rand.randint(0, degraded.note_df.shape[0])
    
    # Shift its pitch (to something new)
    original_pitch = degraded.note_df.loc[note_index, 'pitch']
    while degraded.note_df.loc[note_index, 'pitch'] == original_pitch:
        degraded.note_df.loc[note_index, 'pitch'] = rand.randint(min_pitch, max_pitch)
        
    return degraded



def time_shift(excerpt, rand, params):
    """
    Shift the onset and offset times of one note from the given excerpt,
    leaving its duration unchanged.
    
    Parameters
    ----------
    excerpt : Composition
        A Composition object of an excerpt from a piece of music.
        
    rand : numpy.random
        A seeded numpy random object.
        
    params : dict
        A dictionary containing parameters for the time shift. All used
        parameters keys will begin with 'time_shift_'. They include:
            None
            
    Returns
    -------
    degraded : Composition
        A copy of the given excerpt, with the timing of one note changed.
    """



def onset_shift(excerpt, rand, params):
    """
    Shift the onset time of one note from the given excerpt.
    
    Parameters
    ----------
    excerpt : Composition
        A Composition object of an excerpt from a piece of music.
        
    rand : numpy.random
        A seeded numpy random object.
        
    params : dict
        A dictionary containing parameters for the onset shift. All used
        parameters keys will begin with 'onset_shift_'. They include:
            None
            
    Returns
    -------
    degraded : Composition
        A copy of the given excerpt, with the onset time of one note changed.
    """



def offset_shift(excerpt, rand, params):
    """
    Shift the offset time of one note from the given excerpt.
    
    Parameters
    ----------
    excerpt : Composition
        A Composition object of an excerpt from a piece of music.
        
    rand : numpy.random
        A seeded numpy random object.
        
    params : dict
        A dictionary containing parameters for the offset shift. All used
        parameters keys will begin with 'offset_shift_'. They include:
            None
            
    Returns
    -------
    degraded : Composition
        A copy of the given excerpt, with the offset time of one note changed.
    """



def remove_note(excerpt, rand, params):
    """
    Remove one note from the given excerpt.
    
    Parameters
    ----------
    excerpt : Composition
        A Composition object of an excerpt from a piece of music.
        
    rand : numpy.random
        A seeded numpy random object.
        
    params : dict
        A dictionary containing parameters for the note removal. All used
        parameters keys will begin with 'remove_note_'. They include:
            None
            
    Returns
    -------
    degraded : Composition
        A copy of the given excerpt, with one note removed.
    """
    degraded = excerpt.copy()
    
    # Sample a random note
    note_index = rand.randint(0, degraded.note_df.shape[0])
    
    # Remove that note
    degraded.note_df.drop(0, inplace=True).reset_index(drop=True, inplace=True)
        
    return degraded



def add_note(excerpt, rand, params):
    """
    Add one note to the given excerpt.
    
    Parameters
    ----------
    excerpt : Composition
        A Composition object of an excerpt from a piece of music.
        
    rand : numpy.random
        A seeded numpy random object.
        
    params : dict
        A dictionary containing parameters for the note addition. All used
        parameters keys will begin with 'add_note_'. They include:
            None
            
    Returns
    -------
    degraded : Composition
        A copy of the given excerpt, with one note added.
    """


