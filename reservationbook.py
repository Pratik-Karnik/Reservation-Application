import os
import urllib
import cgi
from google.appengine.api import users
from google.appengine.ext import ndb
import jinja2
import webapp2
import uuid
import time
from datetime import datetime,time,date,timedelta
from time import sleep


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

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

class Resource(ndb.Model):
    resourceId = ndb.StringProperty(indexed=True)
    resourceAuthor = ndb.StructuredProperty(Author)
    resourceName = ndb.StringProperty(indexed=True)
    resourceStartTime = ndb.DateTimeProperty(auto_now_add=False)
    resourceEndTime = ndb.DateTimeProperty(auto_now_add=False)
    numberOfReservations = ndb.IntegerProperty(indexed=False)
    resourceDate = ndb.DateTimeProperty(auto_now_add=False)
    resourceTags = ndb.StringProperty(repeated=True)

class MainPage(webapp2.RequestHandler):
    def get(self):

        pageToDisplay = "yourReservations"

        resourceQuery = Resource.query().order(-Resource.resourceDate)
        resources = resourceQuery.fetch()

        reservationQuery = Reservation.query()
        reservations = reservationQuery.fetch()

        requestedPageToDisplay = self.request.get('pageToDisplay')
        if requestedPageToDisplay != '':
            pageToDisplay = requestedPageToDisplay


        resourceOwner = ""
        ownerView = False

        linkOwnerView = self.request.get('ownerView')
        if linkOwnerView != "":
            ownerView = linkOwnerView

        linkResourceOwner = self.request.get('resourceOwner')
        if linkResourceOwner != "":
            resourceOwner = linkResourceOwner
            ownerView = True

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

        requestedPageToDisplay = self.request.get('pageToDisplay')
        if requestedPageToDisplay != '':
            pageToDisplay = requestedPageToDisplay

        resourceId = self.request.get('resourceId')

        resourceQuery = Resource.query(Resource.resourceId == resourceId)
        resources = resourceQuery.fetch()
        reservationQuery = Reservation.query(Reservation.reservedResourceId == resourceId)
        reservations = reservationQuery.fetch()

        print resources
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
                'resourceStartDate' : resourceStartDate
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
        validReservation = True
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
            print "in first"
            if resource.resourceEndTime >= reservationEndTime:
                print "in second"
                for reservation in reservations:
                    if reservation.reservationStartTime > reservationStartTime and reservation.reservationStartTime >= reservationEndTime:
                        validReservation = True
                    elif reservationStartTime >= reservation.reservationEndTime and reservationEndTime > reservation.reservationEndTime:
                        validReservation = True
                    else:
                        validReservation = False
            else:
                validReservation = False
        else:
            validReservation = False


        if validReservation == True:
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
            query_params = {'pageToDisplay':pageToDisplay,'resourceId':resourceId}
            self.redirect('/reserveResource?' + urllib.urlencode(query_params))


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
            print existingResourceId
            resourceQuery = Resource.query(Resource.resourceId == existingResourceId)
            resourceFetched = resourceQuery.fetch()
            resourceFetched[0].resourceName = resourceName
            resourceFetched[0].resourceStartTime = resourceStartTime
            resourceFetched[0].resourceEndTime = resourceEndTime
            resourceFetched[0].resourceTags = resourceTags
            resourceFetched[0].put()
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
], debug=True)
# [END app]