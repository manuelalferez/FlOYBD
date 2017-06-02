import os
import shutil

from django.conf.urls import url


from . import views
from .earthquakes import viewsEarthquakes
from .weather import viewsWeather
from .gtfs import viewsGTFS

app_name = 'floybd'


urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^weatherStats', viewsWeather.weatherStats, name='weatherStats'),
    url(r'^weather', views.weatherIndex, name='weather'),
    url(r'^gtfs', views.gtfs, name='gtfs'),
    url(r'^dayWeather', viewsWeather.weatherConcreteIndex, name='dayWeather'),
    url(r'^predictWeather', viewsWeather.weatherPredictions, name='predictWeather'),
    url(r'^earthquakes/$', views.eartquakesIndex, name='earthquakes'),
    url('getConcreteDateValues', viewsWeather.getConcreteValues, name='getConcreteDateValues'),
    url('sendConcreteValuesToLG', viewsWeather.sendConcreteValuesToLG, name='sendConcreteValuesToLG'),
    url('getPrediction', viewsWeather.getPrediction, name='getPrediction'),
    url('sendPredictionsToLG', viewsWeather.sendPredictionsToLG, name='sendPredictionsToLG'),
    url('getEarthquakes', viewsEarthquakes.getEarthquakes, name='getEarthquakes'),
    url('sendConcreteEarthquakesValuesToLG', viewsEarthquakes.sendConcreteValuesToLG,
        name='sendConcreteEarthquakesValuesToLG'),
    url('getStats', viewsWeather.getStats, name='getStats'),
    url('sendStatsToLG', viewsWeather.sendStatsToLG, name='sendStatsToLG'),
    url('uploadGTFS', viewsGTFS.uploadGTFS, name='uploadGTFS'),
    url('sendGTFSToLG', viewsGTFS.sendGTFSToLG, name='sendGTFSToLG'),

]


def startup_clean():

    if not os.path.exists("static/kmls"):
        print("Creating kmls folder")
        os.makedirs("static/kmls")
    #else:
    # print("Deletings kmls folder")
     #   shutil.rmtree('static/kmls')
     #   os.makedirs("static/kmls")

startup_clean()