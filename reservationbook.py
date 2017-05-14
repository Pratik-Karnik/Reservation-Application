import os
import urllib
import cgi
from google.appengine.api import users
from google.appengine.ext import ndb
from email import utils
from google.appengine.api import app_identity
from google.appengine.api import mail
import jinja2
import webapp2
import uuid
import time
from datetime import datetime,date,timedelta
from time import sleep
from xml.etree.ElementTree import Element, SubElement, Comment
from xml.etree import ElementTree
from xml.dom import minidom


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

def makePrettyXML(xmlElement):
    rawXML = ElementTree.tostring(xmlElement, 'utf-8')
    parsedXML = minidom.parseString(rawXML)
    return parsedXML.toprettyxml(indent="  ", encoding="UTF-8")

class Author(ndb.Model):
    identity = ndb.StringProperty(indexed=False)
    email = ndb.StringProperty(indexed=False)

class Reservation(ndb.Model):
    reservationId = ndb.StringProperty(indexed=True)
    reservationAuthor = ndb.StructuredProperty(Author)
    reservedResourceName = ndb.StringProperty(indexed=False)
    reservedResourceId = ndb.StringProperty(indexed=True)
    reservationStartTime = ndb.DateTimeProperty(auto_now_add=False)
    reservationEndTime = ndb.DateTimeProperty(auto_now_add=False)
    reservationDuration = ndb.StringProperty(indexed=True)
    reservationPubDate = ndb.DateTimeProperty(auto_now_add=True)

class Resource(ndb.Model):
    resourceId = ndb.StringProperty(indexed=True)
    resourceAuthor = ndb.StructuredProperty(Author)
    resourceName = ndb.StringProperty(indexed=True)
    resourceStartTime = ndb.DateTimeProperty(auto_now_add=False)
    resourceEndTime = ndb.DateTimeProperty(auto_now_add=False)
    numberOfReservations = ndb.IntegerProperty(indexed=False)
    resourceDate = ndb.DateTimeProperty(auto_now_add=False)
    resourceTags = ndb.StringProperty(repeated=True)
    resourcePubDate = ndb.DateTimeProperty(auto_now_add=True)

class MainPage(webapp2.RequestHandler):
    def get(self):

        pageToDisplay = "yourReservations"

        resourceQuery = Resource.query().order(-Resource.resourceDate)
        resources = resourceQuery.fetch()

        reservationQuery = Reservation.query().order(Reservation.reservationStartTime)
        reservations = reservationQuery.fetch()

        requestedPageToDisplay = self.request.get('pageToDisplay')
        if requestedPageToDisplay != '':
            pageToDisplay = requestedPageToDisplay

        resourceOwner = ""
        ownerView = '0'

        linkOwnerView = self.request.get('ownerView')
        if linkOwnerView != "":
            ownerView = linkOwnerView

        linkResourceOwner = self.request.get('resourceOwner')
        if linkResourceOwner != "":
            resourceOwner = linkResourceOwner
            ownerView = '1'

        deletedReservationId = ""
        linkDeletedReservationId = self.request.get('deleteReservation')
        if linkDeletedReservationId != "":
            deletedReservationId = linkDeletedReservationId
            deleteReservationQuery = Reservation.query(Reservation.reservationId == deletedReservationId)
            deletedReservation = deleteReservationQuery.fetch()[0]
            resourceQuery = Resource.query(Resource.resourceId == deletedReservation.reservedResourceId)
            resource = resourceQuery.fetch()[0]
            resource.numberOfReservations = resource.numberOfReservations - 1
            resource.put()
            deletedReservation.key.delete()
            sleep(3)
            query_params = {'pageToDisplay':pageToDisplay}
            self.redirect('/?' + urllib.urlencode(query_params))

        user = users.get_current_user()
        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
            template_values = {
                'user': user,
                'url': url,
                'url_linktext' : url_linktext,
                'pageToDisplay' : pageToDisplay,
                'resources' : resources,
                'reservations' : reservations,
                'ownerView' : ownerView,
                'resourceOwner' : resourceOwner
            }

            template = JINJA_ENVIRONMENT.get_template('index.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect(users.create_login_url(self.request.uri))

class ReserveResource(webapp2.RequestHandler):
    def get(self):

        pageToDisplay = "showReservations"
        validReservation = self.request.get('validReservation')

        requestedPageToDisplay = self.request.get('pageToDisplay')
        if requestedPageToDisplay != '':
            pageToDisplay = requestedPageToDisplay

        resourceId = self.request.get('resourceId')

        resourceQuery = Resource.query(Resource.resourceId == resourceId)
        resources = resourceQuery.fetch()
        reservationQuery = Reservation.query(Reservation.reservedResourceId == resourceId).order(Reservation.reservationStartTime)
        reservations = reservationQuery.fetch()

        user = users.get_current_user()
        resourceStartDate = datetime.strftime(resources[0].resourceStartTime,'%m/%d/%Y')

        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
            template_values = {
                'user': user,
                'url': url,
                'url_linktext' : url_linktext,
                'reservations' : reservations,
                'pageToDisplay' : pageToDisplay,
                'resource' : resources[0],
                'resourceStartDate' : resourceStartDate,
                'validReservation' : validReservation
            }

            template = JINJA_ENVIRONMENT.get_template('reserveResource.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect(users.create_login_url(self.request.uri))


class showTaggedResources(webapp2.RequestHandler):
    def get(self):
        resourceTag = self.request.get('resourceTag')

        resourceQuery = Resource.query(Resource.resourceTags == resourceTag)
        resources = resourceQuery.fetch()

        user = users.get_current_user()

        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
            template_values = {
                'user': user,
                'url': url,
                'url_linktext' : url_linktext,
                'resources' : resources,
            }

            template = JINJA_ENVIRONMENT.get_template('resourceTags.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect(users.create_login_url(self.request.uri))

class AddReservation(webapp2.RequestHandler):
    def post(self):
        validReservation = "1"
        resourceName = self.request.get('resourceName')
        resourceId = self.request.get('resourceId')
        resourceFullDate = self.request.get('resourceDate')
        resourceDate = resourceFullDate.split(" ")[0]

        user = users.get_current_user()
        resourceQuery = Resource.query(Resource.resourceId == resourceId)
        resources = resourceQuery.fetch()
        resource = resources[0]

        reservationQuery = Reservation.query(Reservation.reservedResourceId == resourceId)
        reservations = reservationQuery.fetch()

        startTime = self.request.get('reservationStartTime')
        startTimeArray = startTime.split(':')
        startTimeHours = int(startTimeArray[0])
        startTimeMinutes = int(startTimeArray[1])

        if startTimeHours == 0:
            startTimeHours = 12

        if startTimeHours > 12:
            startTimeHours = startTimeHours-12
            startTimeMeridian = 'PM'
        else:
            startTimeMeridian = 'AM'

        startTime = resourceDate+' '+str(startTimeHours)+':'+str(startTimeMinutes)+' '+startTimeMeridian
        reservationStartTime = datetime.strptime(startTime, '%m/%d/%Y %I:%M %p')

        endTimeHours = self.request.get('endTimeHr')
        endTimeMinutes = self.request.get('endTimeMin')
        endTime = datetime.strptime(endTimeHours+':'+endTimeMinutes, '%H:%M')
        duration = timedelta(hours = endTime.hour, minutes = endTime.minute)
        reservationEndTime = reservationStartTime + duration

        if resource.resourceStartTime <= reservationStartTime:
            if resource.resourceEndTime >= reservationEndTime:
                for reservation in reservations:
                    if reservation.reservationStartTime > reservationStartTime and reservation.reservationStartTime >= reservationEndTime:
                        validReservation = "1"
                    elif reservationStartTime >= reservation.reservationEndTime and reservationEndTime > reservation.reservationEndTime:
                        validReservation = "1"
                    else:
                        validReservation = "0"
            else:
                validReservation = "0"
        else:
            validReservation = "0"

        if validReservation == "1":
            resource.resourceDate = datetime.now()
            resource.numberOfReservations += 1

            resource.put()
            sleep(3)

            newReservation = Reservation()
            newReservation.reservedResourceName = resourceName
            newReservation.reservedResourceId = resourceId
            newReservation.reservationStartTime = reservationStartTime
            newReservation.reservationEndTime = reservationEndTime
            newReservation.reservationDuration = endTimeHours+':'+endTimeMinutes
            newReservation.reservationId = str(uuid.uuid4())

            if users.get_current_user():
                newReservation.reservationAuthor = Author(
                                             identity=users.get_current_user().user_id(),
                                             email=users.get_current_user().email())


            newReservation.put()
            sleep(3)

            pageToDisplay = "yourReservations"
            query_params = {'pageToDisplay':pageToDisplay}
            self.redirect('/?' + urllib.urlencode(query_params))
        else:
            pageToDisplay = "addReservation"
            query_params = {'pageToDisplay':pageToDisplay,'validReservation':validReservation,'resourceId':resourceId}
            self.redirect('/reserveResource?' + urllib.urlencode(query_params))

class seeResourceRSS(webapp2.RequestHandler):
    def get(self):

        resourceId = self.request.get('resourceId')
        reservationQuery = Reservation.query(Reservation.reservedResourceId == resourceId)
        reservations = reservationQuery.fetch()
        reservationNumber = 1

        user = users.get_current_user()
        resourceQuery = Resource.query(Resource.resourceId == resourceId)
        resources = resourceQuery.fetch()
        resource = resources[0]

        resourceUrl = self.request.url
        splitResourceUrl = resourceUrl.split("/")
        reserveResourceLink = ""

        for i in range(0,len(splitResourceUrl)):
            if i != (len(splitResourceUrl) - 1):
                reserveResourceLink += splitResourceUrl[i]+"/"

        reserveResourceLink = reserveResourceLink+"/reserveResource?resourceId="+resourceId

        root = Element('rss')
        root.set('version','2.0')

        channel = SubElement(root, 'channel')
        title = SubElement(channel, 'title')
        title.text = resource.resourceName
        description = SubElement(channel, 'description')
        description.text = "Owner of this resource is "+ resource.resourceAuthor.email
        link = SubElement(channel, 'link')
        link.text = reserveResourceLink

        resourcePubDateTuple = resource.resourcePubDate.timetuple()

        resourcePubDate = time.mktime(resourcePubDateTuple)
        pubDate = SubElement(channel, 'pubDate')
        pubDate.text = utils.formatdate(resourcePubDate)

        lastBuildDate = SubElement(channel, 'lastBuildDate')

        if resource.resourceDate is not None:
            resourceModifiedDateTuple = resource.resourcePubDate.timetuple()
            resourceModifiedDate = time.mktime(resourceModifiedDateTuple)
            lastBuildDate.text = utils.formatdate(resourceModifiedDate)
        else:
            lastBuildDate.text = utils.formatdate(resourcePubDate)


        for reservation in reservations:
            reservationPubDateTuple = reservation.reservationPubDate.timetuple()
            reservationPubDate = time.mktime(reservationPubDateTuple)

            item = SubElement(channel, 'item')
            title = SubElement(item, 'title')
            title.text = "Reservation #"+str(reservationNumber)
            description = SubElement(item, 'description')
            description.text = reservation.reservationAuthor.email+" has made this reservation for duration: "+str(reservation.reservationDuration)+" starting from time: "+str(reservation.reservationStartTime)
            link = SubElement(item, 'link')
            link.text = reserveResourceLink
            guid = SubElement(item, 'guid')
            guid.set('isPermaLink','false')
            guid.text = reservation.reservationId
            pubDate = SubElement(item, 'pubDate')
            pubDate.text = utils.formatdate(reservationPubDate)
            reservationNumber+=1

        rssXML = makePrettyXML(root)


        if user:
            url=users.create_logout_url(self.request.uri)
            url_linktext='Logout'
            
            template_values = {
                'reservations':reservations,
                'user':user,
                'rssXML':rssXML,
            }
            template = JINJA_ENVIRONMENT.get_template('resourceRSS.html')
            self.response.write(template.render(template_values))

        else:
            self.redirect(users.create_login_url(self.request.uri))

class searchResource(webapp2.RequestHandler):
    def get(self):
        resourceName = self.request.get('searchName')
        user = users.get_current_user()
        resourceQuery = Resource.query(Resource.resourceName == resourceName)
        resources = resourceQuery.fetch()

        if user:
            url=users.create_logout_url(self.request.uri)
            url_linktext='Logout'
            
            template_values = {
                'user': user,
                'url': url,
                'url_linktext' : url_linktext,
                'resources' : resources,
            }
            template = JINJA_ENVIRONMENT.get_template('searchResource.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect(users.create_login_url(self.request.uri))

class searchResourceByTime(webapp2.RequestHandler):
    def get(self):
        searchTime = self.request.get('searchTime')
        user = users.get_current_user()
        resourceQuery = Resource.query()
        resources = resourceQuery.fetch()

        availableResources = []

        todaysDate = str(time.strftime("%Y-%m-%d"))
        searchTimeArray = searchTime.split(':')
        searchTimeHours = int(searchTimeArray[0])
        searchTimeMinutes = int(searchTimeArray[1])

        if searchTimeHours == 0:
            searchTimeHours = 12

        if searchTimeHours > 12:
            searchTimeHours = searchTimeHours-12
            searchTimeMeridian = 'PM'
        else:
            searchTimeMeridian = 'AM'

        searchTime = todaysDate+' '+str(searchTimeHours)+':'+str(searchTimeMinutes)+' '+searchTimeMeridian
        resourceSearchTime = datetime.strptime(searchTime, '%Y-%m-%d %I:%M %p')

        endTimeHours = self.request.get('endTimeHr')
        endTimeMinutes = self.request.get('endTimeMin')
        endTime = datetime.strptime(endTimeHours+':'+endTimeMinutes, '%H:%M')
        duration = timedelta(hours = endTime.hour, minutes = endTime.minute)
        resourceEndTime = resourceSearchTime + duration

        for resource in resources:
            resourceDate = str(resource.resourceDate).split(" ")[0]
            if resourceDate == str(todaysDate):
                if resourceSearchTime >= resource.resourceStartTime and resourceEndTime <= resource.resourceEndTime:
                    availableResources.append(resource)

        if user:
            url=users.create_logout_url(self.request.uri)
            url_linktext='Logout'
            
            template_values = {
                'user': user,
                'url': url,
                'url_linktext' : url_linktext,
                'resources' : availableResources,
            }
            template = JINJA_ENVIRONMENT.get_template('searchResource.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect(users.create_login_url(self.request.uri))

class CreateResource(webapp2.RequestHandler):
    def post(self):

        resourceName = self.request.get('resourceName')
        user = users.get_current_user().user_id()

        existingResourceId = ""
        existingResourceId = self.request.get('resourceId')

        if existingResourceId == "":
            resourceDate = self.request.get('resourceDate')
            startTime = self.request.get('resourceStartTime')
            endTime = self.request.get('resourceEndTime')

            startTimeArray = startTime.split(':')
            startTimeHours = int(startTimeArray[0])
            startTimeMinutes = int(startTimeArray[1])

            if startTimeHours == 0:
                startTimeHours = 12

            if startTimeHours > 12:
                startTimeHours = startTimeHours-12
                startTimeMeridian = 'PM'
            else:
                startTimeMeridian = 'AM'

            endTimeArray = endTime.split(':')
            endTimeHours = int(endTimeArray[0])
            endTimeMinutes = int(endTimeArray[1])

            if endTimeHours == 0:
                endTimeHours = 12

            if endTimeHours > 12:
                endTimeHours = endTimeHours-12
                endTimeMeridian = 'PM'
            else:
                endTimeMeridian = 'AM'
        else:
            resourceMonth = self.request.get('Month')
            resourceYear = self.request.get('Year')
            resourceDay = self.request.get('Day')
            resourceDate = resourceYear+"-"+resourceMonth+"-"+resourceDay

            startTimeHours = self.request.get('StartHours')
            startTimeMinutes = self.request.get('StartMinutes')
            startTimeMeridian = self.request.get('startMeridian')

            endTimeHours = self.request.get('EndHours')
            endTimeMinutes = self.request.get('EndMinutes')
            endTimeMeridian = self.request.get('endMeridian')


        tags = self.request.get('resourceTags')
        resourceTags = tags.split(',')

        startTime = resourceDate+' '+str(startTimeHours)+':'+str(startTimeMinutes)+' '+startTimeMeridian
        resourceStartTime = datetime.strptime(startTime, '%Y-%m-%d %I:%M %p')

        endTime = resourceDate+' '+str(endTimeHours)+':'+str(endTimeMinutes)+' '+endTimeMeridian
        resourceEndTime = datetime.strptime(endTime, '%Y-%m-%d %I:%M %p')

        if existingResourceId != "" :
            resourceQuery = Resource.query(Resource.resourceId == existingResourceId)
            resourceFetched = resourceQuery.fetch()
            resourceFetched[0].resourceName = resourceName
            resourceFetched[0].resourceStartTime = resourceStartTime
            resourceFetched[0].resourceEndTime = resourceEndTime
            resourceFetched[0].resourceTags = resourceTags
            resourceFetched[0].put()

            reservationQuery = Reservation.query(Reservation.reservedResourceId == existingResourceId)
            reservations = reservationQuery.fetch()
            for reservation in reservations:
                reservation.reservationStartTime = resourceStartTime
                endTime = datetime.strptime(reservation.reservationDuration, '%H:%M')
                duration = timedelta(hours = endTime.hour, minutes = endTime.minute)
                reservation.reservationEndTime = reservation.reservationStartTime + duration
                reservation.put()
        else:         
            newResource = Resource()
            newResource.resourceName = resourceName
            newResource.resourceStartTime = resourceStartTime
            newResource.resourceDate = datetime.strptime(resourceDate, '%Y-%m-%d')
            newResource.resourceEndTime = resourceEndTime
            newResource.resourceTags = resourceTags
            newResource.numberOfReservations = 0
            newResource.resourceId = str(uuid.uuid4())
            if users.get_current_user():
                newResource.resourceAuthor = Author(
                                             identity=users.get_current_user().user_id(),
                                             email=users.get_current_user().email())

            newResource.put()

        sleep(3)

        pageToDisplay = "allResources"
        query_params = {'pageToDisplay':pageToDisplay}
        self.redirect('/?' + urllib.urlencode(query_params))

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/create', CreateResource),
    ('/reserveResource', ReserveResource),
    ('/addReservation', AddReservation),
    ('/resourceTags', showTaggedResources),
    ('/seeRSS', seeResourceRSS),
    ('/searchResource', searchResource),
    ('/searchResourceByTime', searchResourceByTime)
], debug=True)
# [END app]