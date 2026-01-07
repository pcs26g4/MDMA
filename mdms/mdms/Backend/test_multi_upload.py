import requests
import io
from PIL import Image, ExifTags
import piexif

def create_image_with_gps(lat, lon, filename):
    # Create a small RGB image
    img = Image.new('RGB', (100, 100), color=(73, 109, 137))
    
    # Convert lat/lon to EXIF format
    def to_deg(value, loc):
        if value < 0:
            loc_value = loc[0] if loc == ('S', 'N') else loc[0]
        else:
            loc_value = loc[1] if loc == ('S', 'N') else loc[1]
        abs_value = abs(value)
        deg = int(abs_value)
        t1 = (abs_value - deg) * 60
        min = int(t1)
        sec = round((t1 - min) * 60, 5)
        return (deg, min, sec), loc_value

    lat_deg, lat_ref = to_deg(lat, ('S', 'N'))
    lon_deg, lon_ref = to_deg(lon, ('W', 'E'))

    exif_dict = {"GPS": {
        piexif.GPSIFD.GPSLatitudeRef: lat_ref,
        piexif.GPSIFD.GPSLatitude: [(lat_deg[0], 1), (lat_deg[1], 1), (int(lat_deg[2]*100), 100)],
        piexif.GPSIFD.GPSLongitudeRef: lon_ref,
        piexif.GPSIFD.GPSLongitude: [(lon_deg[0], 1), (lon_deg[1], 1), (int(lon_deg[2]*100), 100)],
    }}
    exif_bytes = piexif.dump(exif_dict)
    img.save(filename, exif=exif_bytes)
    print(f"Created {filename} with GPS {lat}, {lon}")

def test_multi_upload():
    url = "http://127.0.0.1:8000/api/complaints/multi"
    
    # Create test images
    # Location 1: 3 images
    create_image_with_gps(12.9716, 77.5946, "test1_pothole.jpg")
    create_image_with_gps(12.9717, 77.5947, "test2_garbage.jpg")
    create_image_with_gps(12.9718, 77.5948, "test3_street_debris.jpg")
    
    # Location 2: 2 images (1 pothole, 1 garbage)
    create_image_with_gps(13.0827, 80.2707, "test4_pothole.jpg")
    create_image_with_gps(13.0828, 80.2708, "test5_garbage.jpg")

    files = [
        ('files', ('test1_pothole.jpg', open('test1_pothole.jpg', 'rb'), 'image/jpeg')),
        ('files', ('test2_garbage.jpg', open('test2_garbage.jpg', 'rb'), 'image/jpeg')),
        ('files', ('test3_street_debris.jpg', open('test3_street_debris.jpg', 'rb'), 'image/jpeg')),
        ('files', ('test4_pothole.jpg', open('test4_pothole.jpg', 'rb'), 'image/jpeg')),
        ('files', ('test5_garbage.jpg', open('test5_garbage.jpg', 'rb'), 'image/jpeg')),
    ]

    try:
        response = requests.post(url, files=files)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        for _, (name, _, _) in files:
            import os
            try: os.remove(name)
            except: pass

if __name__ == "__main__":
    test_multi_upload()
