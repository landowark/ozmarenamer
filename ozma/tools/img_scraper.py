from google_images_search import GoogleImagesSearch
from PIL import Image
from io import BytesIO
import tempfile
import os
from ozma import config

def search_for_images(search_str:str, number:int=10) -> list:
    search_params = {"q":search_str, 'num':number}
    gis = GoogleImagesSearch(config['google_api_key'], config['google_cx'])
    gis.search(search_params=search_params)
    temporary_files = []
    for iii, result in enumerate(gis.results()):
        my_bytes = BytesIO()
        my_bytes.seek(0)
        raw_img = result.get_raw_data()
        result.copy_to(my_bytes, raw_img)
        my_bytes.seek(0)
        temp_img = Image.open(my_bytes)
        outfile = os.path.join(tempfile.gettempdir(), f"_Image_{iii}.png")
        temp_img.save(outfile, "png")
        temporary_files.append(outfile)
    return temporary_files
