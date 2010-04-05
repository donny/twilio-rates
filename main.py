import os, csv, cStringIO
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from django.utils import simplejson


class CalculatePage(webapp.RequestHandler):
	def get(self, number, duration):
		self.response.headers['Content-Type'] = 'text/plain'

		key = ''

		# Check the parameters
		if not number:
			self.response.out.write('{"status": "ERROR"}')
			return
		if not duration:
			duration = 1

		# Search longest matching prefix
		for i in range(1, len(number)):
			if memcache.get(number[0:i]):
				key = number[0:i]

		if not key:
			self.response.out.write('{"status": "ERROR"}')
			return

		data = simplejson.loads(memcache.get(key))
		data['status'] = 'OK'
		data['duration'] = duration
		data['total_rate'] = str(float(duration) * float(data['rate']))
		self.response.out.write(simplejson.dumps(data))


class MainPage(webapp.RequestHandler):
	def get(self):
		path = os.path.join(os.path.dirname(__file__), 'index.html')
		self.response.out.write(template.render(path, {}))


class UpdatePage(webapp.RequestHandler):
	def get(self):
		self.response.headers['Content-Type'] = 'text/plain'

		rates_url = 'http://www.twilio.com/resources/rates/international-rates.csv'
		rates_data = ''

		# Get the data from Twilio
		try:
			remote_data = urlfetch.fetch(rates_url)
			if remote_data.status_code != 200:
				raise Exception('')
			rates_csv = remote_data.content
			rates_data = csv.reader(cStringIO.StringIO(rates_csv))
		except:
			self.response.out.write('{"status": "ERROR"}')
			return

		# Save the data into memcache (expire in 10 days)
		for row in rates_data:
			country = row[0]
			rate = row[1]
			numbers = row[2].split(' ')
			d = {}
			for number in numbers:
				d[number] = '{"country": "' + country + '", "rate": "' + rate + '"}'
				#memKey = number
				#memVal = '{"country": "' + country + '", "rate": "' + rate + '"}'
				#memcache.set(key = memKey, value = memVal, time = 864000)
			memcache.set_multi(d, time = 864000)

		self.response.out.write('{"status": "OK"}')



application = webapp.WSGIApplication([('/update', UpdatePage),
														(r'/calculate/([0-9]*)/?([0-9]*)', CalculatePage),
														('/.*', MainPage)
														], debug=True)

def main():
	run_wsgi_app(application)

if __name__ == "__main__":
	main()
