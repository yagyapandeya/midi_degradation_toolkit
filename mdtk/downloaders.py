"""
Classes to download data from different source. Each class gets data from one
source. The base data to get is midi. To contribute a new dataset, create a
new class which extends DataDownloader, and write an accompanying test in
./tests/test_downloads.py
"""
import os
import shutil
import urllib



USER_HOME = os.path.expanduser('~')
DEFAULT_CACHE_LOC = os.path.join(USER_HOME, '.mdtk_cache')



class DataDownloader:
    """Base class for data downloaders"""
    def __init__(self, cache_loc=DEFAULT_CACHE_LOC, 
                 midi_output_loc=None, csv_output_loc=None):
        self.dataset_name = self.__class__.__name__
        self.download_urls = []
        self.midi_locations = []
        self.csv_locations = []
        self.cache_loc = cache_loc
        self.output_loc = {'midi': midi_output_loc, 'csv': csv_output_loc}
        
    
    def get_output_and_cache_loc(self, data_type, output_loc=None,
                                 cache_loc=None):
        """Convenience method to allow methods to take the class specified
        output and cache locations, or locations specified in the method
        call arguments."""
        if output_loc is None:
            output_loc = self.output_loc[data_type]
        if cache_loc is None:
            cache_loc = self.cache_loc
        return output_loc, cache_loc
    
    
    @staticmethod
    def download_file(source, dest, verbose=True, overwrite=None):
        """Get a file from a url and save it locally"""
        if verbose:
            print(f'Downloading {source} to {dest}')
        if os.path.exists(dest):
            if overwrite is None:
                print(f'WARNING: {dest} already exists, not downloading')
                return
            if not overwrite:
                raise OSError(f'{dest} already exists')
        try:
            urllib.request.urlretrieve(source, dest)
        except urllib.error.HTTPError as e:
            print(f'Url {source} does not exist')
            raise e
            
        
    
    def download_midi(self, output_loc=None, cache_loc=None):
        """Downloads the MIDI data to output_loc"""
        output_loc, cache_loc = self.get_output_and_cache_loc(
                'midi',
                output_loc,
                cache_loc
            )
        raise NotImplementedError('In order to download MIDI, you must '
                                  'implement the download_midi method.')
        
    
    def download_csv(self, output_loc=None, cache_loc=None):
        """Downloads the csv data to output_loc"""
        output_loc, cache_loc = self.get_output_and_cache_loc(
                'csv',
                output_loc,
                cache_loc
            )
        raise NotImplementedError('In order to download CSV, you must '
                                  'implement the download_midi method.')
        

# TODO: maybe make a base PPDD class and extend this for various options
class PPDDSept2018Monophonic(DataDownloader):
    """Patterns for Preditction Development Dataset. Monophonic data only.
    
    References
    ----------
    https://www.music-ir.org/mirex/wiki/2019:Patterns_for_Prediction
    """
    def __init__(self, cache_loc=DEFAULT_CACHE_LOC, 
                 midi_output_loc=None, csv_output_loc=None):
        self.dataset_name = self.__class__.__name__
        base_url = ('http://tomcollinsresearch.net/research/data/mirex/'
                         'ppdd/ppdd-sep2018')
        sizes = ['small', 'medium', 'large']
        self.download_urls = [os.path.join(base_url, 
                                           f'PPDD-Sep2018_sym_mono_{size}.zip')
                              for size in sizes]
        self.cache_loc = cache_loc
        if not os.path.exists(cache_loc):
            # TODO: handle overwriting?
            os.mkdir(cache_loc)
        self.output_loc = {'midi': midi_output_loc, 'csv': csv_output_loc}
    
    
    def download_and_extract_zips(self, cache_loc=None, overwrite=None):
        cache_loc = self.cache_loc if cache_loc is None else cache_loc
        base_path = os.path.join(cache_loc, self.dataset_name)
        try:
            os.mkdir(base_path)
        except FileExistsError as e:
            if overwrite is True:
                print(f'Deleting existing directory: {base_path}')
                shutil.rmtree(base_path)
                os.mkdir(base_path)
            elif overwrite is None:
                print(f'WARNING: {base_path} already exists, writing files '
                       'within here only if they do not already exist.')
            elif overwrite is False:
                raise e
            else:
                raise ValueError('overwrite should be boolean or None, not '
                                 f'"{overwrite}"')
        for url in self.download_urls:
            filename = os.path.basename(url)
            self.download_file(url, os.path.join(base_path, filename),
                               overwrite=overwrite)
        
    
    
    
    

class PPDDSept2018Polyphonic(PPDDSept2018Monophonic):
    pass
    
    
    
    
    
    
    
    