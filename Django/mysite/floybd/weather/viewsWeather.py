from django.shortcuts import render
from ..models import Station

import requests
import os
import json
import time
import datetime
from datetime import timedelta
import simplekml
from ..utils.utils import *
from django.http import JsonResponse


def getConcreteValues(request):
    date = request.POST['date']
    station_id = request.POST.get('station', 0)
    allStations = request.POST.get('allStations', 0)

    sparkIp = getSparkIp()
    ip = getDjangoIp()

    getAllStations = allStations == str(1)

    stations = Station.objects.all()

    response = requests.get(
        'http://' + sparkIp + ':5000/getMeasurement?date=' + date + '&station_id=' + station_id + '&allStations=' + str(
            getAllStations), stream=True)
    jsonData = json.loads(response.json())

    stationsWeather = {}
    if len(jsonData) == 0:
        return render(request, 'floybd/weather/weatherConcreteView.html',
                      {'noData': True, 'date': date})

    for row in jsonData:
        concreteStation = Station.objects.get(station_id=row.get("station_id"))
        stationData = {}

        timestamp = row.get("measure_date")
        measureDate = datetime.datetime.utcfromtimestamp(float(timestamp) / 1000).strftime('%d-%m-%Y')
        contentString = '<div id="content">' + \
                        '<div id="siteNotice">' + \
                        '</div>' + \
                        '<h1 id="firstHeading" class="firstHeading">' + concreteStation.name + '</h1>' + \
                        '<h3>' + measureDate + '</h3>' + \
                        '<div id="bodyContent">' + \
                        '<p>' + \
                        '<br/><b>Max Temp: </b>' + str(row.get("max_temp")) + \
                        '<br/><b>Med Temp: </b>' + str(row.get("med_temp")) + \
                        '<br/><b>Min Temp: </b>' + str(row.get("min_temp")) + \
                        '<br/><b>Max Pressure: </b>' + str(row.get("max_pressure")) + \
                        '<br/><b>Min Pressure: </b>' + str(row.get("min_pressure")) + \
                        '<br/><b>Precip: </b>' + str(row.get("precip")) + \
                        '<br/><b>Insolation: </b>' + str(row.get("insolation")) + \
                        '</p>' + \
                        '</div>' + \
                        '</div>'
        stationData["timestamp"] = timestamp
        stationData["measureDate"] = measureDate
        stationData["contentString"] = contentString
        stationData["latitude"] = concreteStation.latitude
        stationData["longitude"] = concreteStation.longitude
        stationData["name"] = concreteStation.name
        stationsWeather[row.get("station_id")] = stationData

    if getAllStations:
        kml = simplekml.Kml()
        for key, value in stationsWeather.items():
            kml.newpoint(name=value["name"], description=value["contentString"],
                         coords=[(value["longitude"], value["latitude"])])

        millis = int(round(time.time() * 1000))
        fileName = "measurement_" + str(date) + "_" + str(millis) + ".kml"
        currentDir = os.getcwd()
        dir1 = os.path.join(currentDir, "static/kmls")
        dirPath2 = os.path.join(dir1, fileName)

        kml.save(dirPath2)
        return render(request, 'floybd/weather/weatherConcreteView.html',
                      {'kml': 'http://' + ip + ':8000/static/kmls/' + fileName, 'date': date})
    else:
        concreteStation = Station.objects.get(station_id=station_id)
        contentString = stationsWeather[station_id]["contentString"]
        return render(request, 'floybd/weather/weatherConcreteView.html',
                      {'stations': stations, 'concreteStation': concreteStation,
                       'weatherData': contentString, 'date': date})


def sendConcreteValuesToLG(request):
    date = request.POST['date']
    millis = int(round(time.time() * 1000))

    allStations = request.POST.get('allStations', 0)

    sparkIp = getSparkIp()

    if str(allStations) == str(1):
        fileurl = request.POST['fileUrl']
        millis = int(round(time.time() * 1000))

        fileName = "measurement_" + str(date) + "_" + str(millis) + ".kml"
        currentDir = os.getcwd()
        dir1 = os.path.join(currentDir, "static/kmls")
        dirPath2 = os.path.join(dir1, fileName)

        response = requests.get(
            'http://' + sparkIp + ':5000/getAllStationsMeasurementsKML?date=' + date,
            stream=True)
        with open(dirPath2, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
        print(fileName)
        sendKmlGlobal(fileName)

        return render(request, 'floybd/weather/weatherConcreteView.html',
                      {'kml': fileurl, 'date': date})

    else:
        station_id = request.POST['station']
        weatherData = request.POST['weatherData']

    fileName = "measurement_" + str(date) + "_" + str(millis) + ".kml"
    currentDir = os.getcwd()
    dir1 = os.path.join(currentDir, "static/kmls")
    dirPath2 = os.path.join(dir1, fileName)

    response = requests.get('http://' + sparkIp + ':5000/getMeasurementKml?date='
                            + date + '&station_id=' + station_id, stream=True)
    with open(dirPath2, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)

    stations = Station.objects.all()
    concreteStation = Station.objects.get(station_id=station_id)

    sendKml(fileName, concreteStation)

    return render(request, 'floybd/weather/weatherConcreteView.html',
                  {'stations': stations, 'concreteStation': concreteStation,
                   'weatherData': weatherData, 'date': date})


def weatherConcreteIndex(request):
    stations = Station.objects.all()
    return render(request, 'floybd/weather/weatherConcrete.html', {'stations': stations})


def weatherPredictions(request):
    stations = Station.objects.all()
    columnsList = ["max_temp", "med_temp", "min_temp", "max_pressure", "min_pressure",
                   "precip", "insolation"]
    return render(request, 'floybd/weather/weatherPrediction.html',
                  {'stations': stations, 'columnsList': columnsList})


def getPrediction(request):
    station_id = request.POST['station']
    columnsToPredict = request.POST.getlist('columnToPredict')

    sparkIp = getSparkIp()
    ip = getDjangoIp()

    jsonData = {"station_id": station_id, "columnsToPredict": columnsToPredict}
    payload = json.dumps(jsonData)

    response = requests.post('http://' + sparkIp + ':5000/getPrediction',
                             headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
                             data=payload)

    if response.json():
        result = json.loads(response.json())
        concreteStation = Station.objects.get(station_id=station_id)
        predictionStr = ""

        for row in result:
            jsonRow = json.loads(row)
            kml = simplekml.Kml()

            for column in columnsToPredict:
                if jsonRow.get("prediction_" + column) is not None:
                    predictionStr += '<br/><b>' + column + ': </b>' + str(jsonRow.get("prediction_" + column))

        contentString = '<div id="content">' + \
                        '<div id="siteNotice">' + \
                        '</div>' + \
                        '<div id="bodyContent">' + \
                        '<p>' + predictionStr + '</p>' + \
                        '</div>' + \
                        '</div>'
        kml.newpoint(name=concreteStation.name, description=contentString,
                     coords=[(concreteStation.longitude, concreteStation.latitude)])

        millis = int(round(time.time() * 1000))
        fileName = "prediction_" + str(millis) + ".kml"
        currentDir = os.getcwd()
        dir1 = os.path.join(currentDir, "static/kmls")
        dirPath2 = os.path.join(dir1, fileName)

        kml.save(dirPath2)

        kmlpath = "http://" + ip + ":8000/static/kmls/" + fileName

        return render(request, 'floybd/weather/weatherPredictionView.html',
                      {'fileName': fileName, 'kml': kmlpath,
                       'concreteStation': concreteStation})
    else:
        return render(request, 'floybd/weather/weatherPredictionView.html')


def sendPredictionsToLG(request):
    fileName = request.POST.get("fileName")
    ip = getDjangoIp()
    kmlpath = "http://" + ip + ":8000/static/kmls/" + fileName

    station_id = request.POST.get("station_id")
    stats = request.POST.get("stats", 0)

    concreteStation = Station.objects.get(station_id=station_id)

    sendKml(fileName, concreteStation)

    time.sleep(1)
    command = "echo 'playtour=Show Balloon' | sshpass -p lqgalaxy ssh lg@" + getLGIp() + \
              " 'cat - > /tmp/query.txt'"
    os.system(command)

    return render(request, 'floybd/weather/weatherPredictionView.html',
                  {'fileName': fileName, 'kml': kmlpath,
                   'concreteStation': concreteStation, 'stats': stats == str("1")})


def weatherStats(request):
    stations = Station.objects.all()
    return render(request, 'floybd/weather/weatherStats.html', {'stations': stations})


def getStats(request):
    stations = Station.objects.all()

    ip = getDjangoIp()

    allStations = request.POST.get('allStations', 0)
    allTime = request.POST.get('allTime', 0)
    dateFrom = request.POST.get('dateFrom', 0)
    dateTo = request.POST.get('dateTo', 0)
    station_id = request.POST.get('station', 0)
    addGraphs = request.POST.get('addGraphs', 0)

    addGraphs = (addGraphs == str("1"))

    print("AllStations:", allStations)
    print("allTime:", allTime)
    print("dateFrom:", dateFrom)
    print("dateTo:", dateTo)
    print("station_id:", station_id)
    print("addGraphs:", addGraphs)

    jsonData = {"station_id": station_id, "dateTo": dateTo, "dateFrom": dateFrom, "allTime": allTime,
                "allStations": allStations}

    payload = json.dumps(jsonData)

    response = requests.post('http://130.206.117.178:5000/getStats',
                             headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
                             data=payload)

    result = json.loads(response.json())
    intervalData = None
    oneStation = (allStations != str(1))
    if allTime != str(1) and allStations != str(1):
        intervalData = True

    stationsWeather = {}
    kml = simplekml.Kml()
    for row in result:
        concreteStation = Station.objects.get(station_id=row.get("station_id"))
        stationData = {}

        if allTime == str(1):
            if addGraphs:
                contentString = getContentStringWithGraphs(row, concreteStation)
            else:
                contentString = '<div id="content">' + \
                                '<div id="siteNotice">' + \
                                '</div>' + \
                                '<h1 id="firstHeading" class="firstHeading">' + concreteStation.name + '</h1>' + \
                                '<div id="bodyContent">' + \
                                '<br/><b>Avg Max Temp: </b>' + str(row.get("avgMaxTemp")) + \
                                '<br/><b>Avg Med Temp: </b>' + str(row.get("avgMedTemp")) + \
                                '<br/><b>Avg Min Temp: </b>' + str(row.get("avgMinTemp")) + \
                                '<br/><b>Avg Max Pressure: </b>' + str(row.get("avgMaxPressure")) + \
                                '<br/><b>Avg Min Pressure: </b>' + str(row.get("min_pressure")) + \
                                '<br/><b>Avg Precip: </b>' + str(row.get("avgPrecip")) + \
                                '<br/><b>Max Max Temp: </b>' + str(row.get("maxMaxTemp")) + \
                                '<br/><b>Min Max Temp: </b>' + str(row.get("minMaxTemp")) + \
                                '<br/><b>Max Med Temp: </b>' + str(row.get("maxMedTemp")) + \
                                '<br/><b>Min Med Temp: </b>' + str(row.get("minMedTemp")) + \
                                '<br/><b>Max Min Temp: </b>' + str(row.get("maxMinTemp")) + \
                                '<br/><b>Min Min Temp: </b>' + str(row.get("minMinTemp")) + \
                                '<br/><b>Max Precip: </b>' + str(row.get("maxPrecip")) + \
                                '</div>' + \
                                '</div>'
        else:
            contentString = '<div id="content">' + \
                            '<div id="siteNotice">' + \
                            '</div>' + \
                            '<h1 id="firstheading" class="firstheading">' + concreteStation.name + '</h1>' + \
                            '<div id="bodycontent">' + \
                            '<p>' + \
                            '<br/><b>Avg max temp: </b>' + str(row.get("avg(max_temp)")) + \
                            '<br/><b>Avg med temp: </b>' + str(row.get("avg(med_temp)")) + \
                            '<br/><b>Avg min temp: </b>' + str(row.get("avg(min_temp)")) + \
                            '<br/><b>Avg max pressure: </b>' + str(row.get("avg(max_pressure)")) + \
                            '<br/><b>Avg min pressure: </b>' + str(row.get("avg(min_pressure)")) + \
                            '<br/><b>Avg precip: </b>' + str(row.get("avg(precip)")) + \
                            '<br/><b>Avg insolation: </b>' + str(row.get("avg(insolation)")) + \
                            '</p>' + \
                            '</div>' + \
                            '</div>'

        stationData["contentString"] = contentString
        stationData["latitude"] = concreteStation.latitude
        stationData["longitude"] = concreteStation.longitude
        stationData["name"] = concreteStation.name
        stationsWeather[row.get("station_id")] = stationData

        point = kml.newpoint(name=stationData["name"], description=stationData["contentString"],
                     coords=[(stationData["longitude"], stationData["latitude"])])

        point.style.balloonstyle.bgcolor = simplekml.Color.lightblue
        point.style.balloonstyle.text = stationData["contentString"]
        point.gxballoonvisibility = 0

        tour = kml.newgxtour(name="Show Balloon")
        playlist = tour.newgxplaylist()

        animatedupdateshow = playlist.newgxanimatedupdate(gxduration=0.1)
        animatedupdateshow.update.change = '<Placemark targetId="{0}"><visibility>1</visibility>' \
                                           '<gx:balloonVisibility>1</gx:balloonVisibility></Placemark>' \
            .format(point.placemark.id)

    millis = int(round(time.time() * 1000))
    fileName = "stats_" + str(millis) + ".kml"
    currentDir = os.getcwd()
    dir1 = os.path.join(currentDir, "static/kmls")
    dirPath2 = os.path.join(dir1, fileName)
    concreteStation = Station.objects.get(station_id=station_id)

    kml.save(dirPath2)

    return render(request, 'floybd/weather/weatherStats.html', {'kml': 'http://' + ip + ':8000/static/kmls/' + fileName,
                                                                'stations': stations, 'fileName': fileName,
                                                                'intervalData': intervalData, "dateTo": dateTo,
                                                                "dateFrom": dateFrom, "station": station_id,
                                                                'concreteStation': concreteStation,
                                                                'oneStation': oneStation,
                                                                'allTime': allTime == str("1")})


def getContentStringWithGraphs(rowData, station):
    print("Getting Graphs...")
    print(rowData)
    contentString = '<table width="500px"><tr><td class="balloonTd">'+\
                    '<h3>Max Temp</h3>' + \
                    '<br/><b>Avg Max Temp: </b>' + str(rowData.get("avgMaxTemp")) + \
                    '<br/><b>Max Max Temp: </b>' + str(rowData.get("maxMaxTemp")) + \
                    '<br/><b>Min Max Temp: </b>' + str(rowData.get("minMaxTemp")) + \
                    '<br/><img width="100%" height="auto" src="http://130.206.117.178:5000/' \
                    'getStatsImage?station_id=' + rowData.get("station_id") + '&imageType=max_temp"/> ' + \
                    '</td><td class="balloonTd">' + \
                    '<h3>Med Temp</h3>' + \
                    '<br/><b>Avg Med Temp: </b>' + str(rowData.get("avgMedTemp")) + \
                    '<br/><b>Max Med Temp: </b>' + str(rowData.get("maxMedTemp")) + \
                    '<br/><b>Min Med Temp: </b>' + str(rowData.get("minMedTemp")) + \
                    '<br/><img width="100%" height="auto" src="http://130.206.117.178:5000/' \
                    'getStatsImage?station_id=' + rowData.get("station_id") + '&imageType=med_temp"/> ' + \
                    '</td><td class="balloonTd">' + \
                    '<h3>Min Temp</h3>' + \
                    '<br/><b>Avg Min Temp: </b>' + str(rowData.get("avgMinTemp")) + \
                    '<br/><b>Max Min Temp: </b>' + str(rowData.get("maxMinTemp")) + \
                    '<br/><b>Min Min Temp: </b>' + str(rowData.get("minMinTemp")) + \
                    '<br/><img width="100%" height="auto" src="http://130.206.117.178:5000/' \
                    'getStatsImage?station_id=' + rowData.get("station_id") + '&imageType=min_temp"/>' + \
                    '</td></tr><tr><td class="balloonTd">' + \
                    '<h3>Max Pressure</h3>' + \
                    '<br/><b>Avg Max Pressure: </b>' + str(rowData.get("avgMaxPressure")) + \
                    '<br/><img width="100%" height="auto" src="http://130.206.117.178:5000/' \
                    'getStatsImage?station_id=' + rowData.get("station_id") + '&imageType=max_pressure"/>' + \
                    '</td><td class="balloonTd">' + \
                    '<h3>Min Pressure</h3>' + \
                    '<br/><b>Avg Min Pressure: </b>' + str(rowData.get("avgMinPressure")) + \
                    '<br/><img width="100%" height="auto" src="http://130.206.117.178:5000/' \
                    'getStatsImage?station_id=' + rowData.get("station_id") + '&imageType=min_pressure"/> ' + \
                    '</td><td class="balloonTd">' + \
                    '<h3>Precipitation</h3>' + \
                    '<br/><b>Avg Precip: </b>' + str(rowData.get("avgPrecip")) + \
                    '<br/><b>Max Precip: </b>' + str(rowData.get("maxPrecip")) + \
                    '<br/><img width="100%" height="auto" src="http://130.206.117.178:5000/' \
                    'getStatsImage?station_id=' + rowData.get("station_id") + '&imageType=precip"/>' + \
                    '</td></tr></table>'

    return contentString


def getGraphDataForStats(request):
    station_id = request.GET.get("station")
    dateFrom = request.GET.get("dateFrom")
    dateTo = request.GET.get("dateTo")

    jsonData = {"station_id": station_id, "dateTo": dateTo, "dateFrom": dateFrom}
    payload = json.dumps(jsonData)

    response = requests.post('http://' + getSparkIp() + ':5000/getWeatherDataInterval',
                             headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
                             data=payload)

    result = json.loads(response.json())
    if result:
        data = {
            'stationData': result
        }
    else:
        data = {}

    return JsonResponse(data)


def sendKmlGlobal(fileName):
    ip = getDjangoIp()
    lgIp = getLGIp()
    command = "echo 'http://" + str(ip) + ":8000/static/kmls/" + fileName + "' | sshpass -p lqgalaxy ssh lg@" + str(lgIp) + \
              " 'cat - > /var/www/html/kmls.txt'"
    os.system(command)


def sendKml(fileName, concreteStation):
    ip = getDjangoIp()
    lgIp = getLGIp()

    command = "echo 'http://" + ip + ":8000/static/kmls/" + fileName + "' | sshpass -p lqgalaxy ssh lg@" + lgIp +\
              " 'cat - > /var/www/html/kmls.txt'"
    os.system(command)

    if concreteStation is not None:
        flyTo = "flytoview=<LookAt>" \
                + "<longitude>" + str(concreteStation.longitude) + "</longitude>" \
                + "<latitude>" + str(concreteStation.latitude) + "</latitude>" \
                + "<altitude>100</altitude>" \
                + "<heading>14</heading>" \
                + "<tilt>69</tilt>" \
                + "<range>200000</range>" \
                + "<altitudeMode>relativeToGround</altitudeMode>" \
                + "<gx:altitudeMode>relativeToSeaFloor</gx:altitudeMode></LookAt>"

        command = "echo '" + flyTo + "' | sshpass -p lqgalaxy ssh lg@" + lgIp + " 'cat - > /tmp/query.txt'"
        os.system(command)


def sendStatsToLG(request):
    fileName = request.POST.get("fileName")
    sendKmlGlobal(fileName)
    stations = Station.objects.all()

    allStations = request.POST.get('allStations', 0)
    allTime = request.POST.get('allTime', 0)
    dateFrom = request.POST.get('dateFrom', 0)
    dateTo = request.POST.get('dateTo', 0)
    station_id = request.POST.get('station', 0)
    station = request.POST.get('station', 0)
    concreteStation = Station.objects.get(station_id=station)

    oneStation = not allStations
    intervalData = False
    if not allTime and not allStations:
        intervalData = True

    if oneStation:
        flyTo = "flytoview=<LookAt>" \
                + "<longitude>" + str(concreteStation.longitude) + "</longitude>" \
                + "<latitude>" + str(concreteStation.latitude) + "</latitude>" \
                + "<altitude>100</altitude>" \
                + "<heading>14</heading>" \
                + "<tilt>69</tilt>" \
                + "<range>200000</range>" \
                + "<altitudeMode>relativeToGround</altitudeMode>" \
                + "<gx:altitudeMode>relativeToSeaFloor</gx:altitudeMode>" \
                  "<gx:duration>2</gx:duration></LookAt>"

        command = "echo '" + flyTo + "' | sshpass -p lqgalaxy ssh lg@" + getLGIp() + " 'cat - > /tmp/query.txt'"
        os.system(command)

    time.sleep(7)
    command = "echo 'playtour=Show Balloon' | sshpass -p lqgalaxy ssh lg@" + getLGIp() + \
              " 'cat - > /tmp/query.txt'"
    os.system(command)

    ip = getDjangoIp()

    return render(request, 'floybd/weather/weatherStats.html', {'kml': 'http://' + ip + ':8000/static/kmls/' + fileName,
                                                                'stations': stations, 'fileName': fileName,
                                                                'intervalData': intervalData, "dateTo": dateTo,
                                                                "dateFrom": dateFrom, "station": station_id,
                                                                'concreteStation': concreteStation,
                                                                'oneStation': oneStation,
                                                                'allTime': allTime})


def citydashboard(request):
    stations = Station.objects.all()
    return render(request, 'floybd/weather/indexDashboard.html', {'stations': stations})


def viewDashboard(request):
    station = request.GET.get('station', None)
    daysBefore = request.GET.get('daysBefore', None)

    sparkIp = getSparkIp()

    today = time.strftime("%Y-%m-%d")
    previousDate = datetime.datetime.today() - timedelta(days=int(daysBefore))
    jsonData = {"station_id": station, "dateTo": today, "dateFrom": previousDate.strftime("%Y-%m-%d")}

    payload = json.dumps(jsonData)

    response = requests.post('http://' + sparkIp + ':5000/getWeatherDataInterval',
                             headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
                             data=payload)

    result = json.loads(response.json())
    if result:
        data = {
            'stationData': result
        }
    else:
        data = {}
    return JsonResponse(data)


def weatherPredictionsStats(request):
    stations = Station.objects.all()

    return render(request, 'floybd/weather/weatherPredictionStats.html',
                  {'stations': stations})


def getPredictionStats(request):
    today = time.strftime("%Y-%m-%d")
    station_id = request.POST['station']
    sparkIp = getSparkIp()
    ip = getDjangoIp()

    jsonData = {"station_id": station_id, "fecha": today}
    payload = json.dumps(jsonData)

    response = requests.post('http://' + sparkIp + ':5000/getPredictionStats',
                             headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
                             data=payload)

    if response.json():
        result = json.loads(response.json())
        concreteStation = Station.objects.get(station_id=station_id)
        kml = simplekml.Kml()
        if len(result) > 0:
            contentString = '<div id="content">' + \
                            '<div id="siteNotice">' + \
                            '</div>' + \
                            '<h3 id="firstheading" class="firstheading">' + concreteStation.province + '</h3>' + \
                            '<div id="bodycontent">' + \
                            '<p>' + \
                            '<br/><b>Max temp: </b>' + str(result[0].get("max_temp")) + \
                            '<br/><b>Med temp: </b>' + str(result[0].get("med_temp")) + \
                            '<br/><b>Min temp: </b>' + str(result[0].get("min_temp")) + \
                            '<br/><b>Max pressure: </b>' + str(result[0].get("max_pressure")) + \
                            '<br/><b>Min pressure: </b>' + str(result[0].get("min_pressure")) + \
                            '<br/><b>Precip: </b>' + str(result[0].get("precip")) + \
                            '<br/><b>Insolation: </b>' + str(result[0].get("insolation")) + \
                            '</p>' + \
                            '</div>' + \
                            '</div>'

            point = kml.newpoint(name=concreteStation.name, description=contentString,
                         coords=[(concreteStation.longitude, concreteStation.latitude)])

            point.style.balloonstyle.bgcolor = simplekml.Color.lightblue
            point.gxballoonvisibility = 0

            tour = kml.newgxtour(name="Show Balloon")
            playlist = tour.newgxplaylist()

            animatedupdateshow = playlist.newgxanimatedupdate(gxduration=0.1)
            animatedupdateshow.update.change = '<Placemark targetId="{0}"><visibility>1</visibility>' \
                                               '<gx:balloonVisibility>1</gx:balloonVisibility></Placemark>' \
                .format(point.placemark.id)

        millis = int(round(time.time() * 1000))
        fileName = "prediction_" + str(millis) + ".kml"
        currentDir = os.getcwd()
        dir1 = os.path.join(currentDir, "static/kmls")
        dirPath2 = os.path.join(dir1, fileName)

        kml.save(dirPath2)

        kmlpath = "http://" + ip + ":8000/static/kmls/" + fileName

        return render(request, 'floybd/weather/weatherPredictionView.html',
                      {'fileName': fileName, 'kml': kmlpath,
                       'concreteStation': concreteStation, 'stats': True})
    else:
        return render(request, 'floybd/weather/weatherPredictionView.html')
