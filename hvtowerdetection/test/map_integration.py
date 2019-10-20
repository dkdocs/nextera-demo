import os
import csv
import fiona
from osgeo import gdal, osr
import geopandas as gpd
from shapely.geometry import Point

## add fiona support
fiona.drvsupport.supported_drivers['kml'] = 'rw' # enable KML support which is disabled by default
fiona.drvsupport.supported_drivers['KML'] = 'rw' # enable KML support which is disabled by default
fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'


class MapIntegration:
    def __init__(self):
        pass

    def get_geo_extents(self, path):
        ds = gdal.Open(path)
        ulx, xres, xskew, uly, yskew, yres = ds.GetGeoTransform()
        lrx = ulx + (ds.RasterXSize * xres)
        lry = uly + (ds.RasterYSize * yres)

        return ds, ulx, uly, lrx, lry

    # get latitude and longitude values
    def get_lat_lon(self, ds, posX, posY):
        print('posX, posY: {}, {}'.format(posX, posY))
        # get CRS from dataset
        crs = osr.SpatialReference()
        crs.ImportFromWkt(ds.GetProjectionRef())
        # create lat/long crs with WGS84 datum
        crsGeo = osr.SpatialReference()
        crsGeo.ImportFromEPSG(4326)  # 4326 is the EPSG id of lat/long crs
        t = osr.CoordinateTransformation(crs, crsGeo)
        (lon, lat, z) = t.TransformPoint(posX, posY)
        print('lat, lon: {}, {}'.format(lat, lon))
        return lat, lon

    # get geo coordinates of objects detected
    def get_object_geo_coordinates(self, path, image_coords):
        # open the dataset and get the geo transform matrix
        print('\npath: {}'.format(path))
        ds = gdal.Open(path)
        xoffset, px_w, rot1, yoffset, rot2, px_h = ds.GetGeoTransform()
        print('\nxoffset, px_w, rot1, yoffset, px_h, rot2: {}, {}, {}, {}, {}, {}'.format(xoffset, px_w, rot1, yoffset, rot2, px_h))

        geo_coords = list()
        for c in image_coords:
            x, y = c[1], c[0]
            # supposing x and y are your pixel coordinate this
            # is how to get the coordinate in space.
            posY = px_w * x + rot1 * y + xoffset
            posX = rot2 * x + px_h * y + yoffset

            # shift to the center of the pixel
            posX += px_w / 2.0
            posY += px_h / 2.0

            print('\nimgX, imgY: {}, {}'.format(x, y))
            geo_coords.append(self.get_lat_lon(ds, posX, posY))

        return geo_coords

    # save shapefile
    def save_object_locations_shapefile(self, geo_coords, save_path):
        shapely_point = []
        for p in geo_coords:
            temp_pt = Point(p)
            shapely_point.append(temp_pt)

        crs={'init': 'epsg:4326'}
        df = gpd.GeoDataFrame(geometry=shapely_point, crs=crs)
        df['id'] = df.index + 1    
        df.to_file(save_path, driver='ESRI Shapefile')
        df.to_file('test/results/xyz.kml', driver='KML')


    # save latitiude/longitude of object locations in a csv file
    def save_lat_lon_csv(self, img_coords, geo_coords, save_path):
        with open(save_path, 'w', newline='') as f:
            csv_writer = csv.writer(f, delimiter=',')
            csv_writer.writerow(['index', 'X_img', 'Y_img', 'latitude', 'longitude'])
            for i in range(len(geo_coords)):
                csv_writer.writerow([os.getenv('OBJECT_TYPE'), img_coords[i][0], img_coords[i][1], geo_coords[i][1], geo_coords[i][0]])

            f.close()
        print('\nCSV file created successfully ...\n')
