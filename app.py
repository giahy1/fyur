#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import (
    Flask, 
    render_template, 
    request, 
    Response, 
    flash, 
    redirect, 
    url_for)
from flask_moment import Moment
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_migrate import Migrate
from flask_wtf import Form
from forms import *
from models import db, Venue, Artist, Show, Genre
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#
# pg_ctl -D "D:\PostgreSQL\16\data" start ; run sever

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db.init_app(app)
migrate = Migrate(app, db)


#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#
# Define association table for many-to-many relationship between Artist and Genre
# Model View
class SearchResponse:
  def __init__(self, count, data):
      self.count=count
      self.data=data
class SearchData:
  def __init__(self, id, name,num_upcoming_shows):
      self.id=id
      self.name=name
      self.num_upcoming_shows=num_upcoming_shows
class DataDetail:
  def __init__(self, data,past_shows,upcoming_shows,genres):
      self.id = data.id
      self.name = data.name
      self.genres = genres
      self.address = data.address if hasattr(data, 'address') else None
      self.city = data.city 
      self.state = data.state 
      self.phone = data.phone 
      self.website = data.website 
      self.facebook_link = data.facebook_link 
      self.seeking_talent = data.seeking_talent if hasattr(data, 'seeking_talent') else None
      self.seeking_venue = data.seeking_venue if hasattr(data, 'seeking_venue') else None
      self.seeking_description = data.seeking_description
      self.image_link = data.image_link
      self.past_shows = past_shows
      self.upcoming_shows = upcoming_shows
      self.past_shows_count = len(past_shows)
      self.upcoming_shows_count = len(upcoming_shows)

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  venues = Venue.query.all()
  now = datetime.now()
  venue_data_dict = {}
  data = []
  for venue in venues:
    city_state_tuple = (venue.city, venue.state)
    num_upcoming_shows = sum(1 for show in venue.shows if show.start_time >= now)
    venue_dic = {"id": venue.id,"name": venue.name,"num_upcoming_shows": num_upcoming_shows,}
    if city_state_tuple not in venue_data_dict.keys():
      venue_data_dict[city_state_tuple] = [venue_dic]
    else:
      venue_data_dict[city_state_tuple].append(venue_dic)
  for (city,state),venue in venue_data_dict.items():
     data.append({"city":city,"sate":state,"venues":venue})
  return render_template('pages/venues.html', areas=data);
@app.route('/venues/search', methods=['POST'])
def search_venues():
  # Get the search term from the form
  search_term = request.form.get('search_term')
  # Query venues based on the search term (case-insensitive)
  venues = Venue.query.filter(Venue.name.ilike(f"%{search_term}%")).all()
  # Get current datetime
  now = datetime.now()
  # Get length of venues
  len_venues = len(venues)
  # Initialize response object
  response = SearchResponse(count=len_venues,data=[])
  for venue in venues:
    # Count the number of upcoming shows
    num_upcoming_shows = sum(1 for show in venue.shows if show.start_time >= now)
    # Append venue data to response
    response.data.append(SearchData(id=venue.id,name=venue.name,num_upcoming_shows = num_upcoming_shows))
  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # Get venue details from the database by id
  venue = Venue.query.filter_by(id = venue_id).first()
  # Get genre names
  genres_names = [genre.name for genre in venue.genres] 
  # Get current datetime
  now = datetime.now()
  # Declare lists to store past and upcoming shows
  past_shows = []
  upcoming_shows = []
  for show in venue.shows:
    # Create a dictionary for the show details
    show_dict = {
          "artist_id": show.artist_id,
          "artist_name": show.artist.name,
          "artist_image_link": show.artist.image_link,
          "start_time": show.start_time.strftime("%m/%d/%Y, %H:%M")
    }
    # Determine if the show is past or upcoming and append to upcoming_shows or past_shows list
    if show.start_time >= datetime.now():
      upcoming_shows.append(show_dict)
    else:
      past_shows.append(show_dict)
  # Create a DataDetail object with venue details
  data = DataDetail(data= venue,past_shows = past_shows,upcoming_shows=upcoming_shows,genres=genres_names)
  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  # Retrieve genres based on selected genre names
  
  form = VenueForm(request.form,meta={'csrf': False})
  genres = Genre.query.filter(Genre.name.in_(form.genres.data)).all()
  # Init Data
  data = {}
  if form.validate():
    try:
        # Create a new Venue object with form data
        venue = Venue(
            name= form.name.data,
            city= form.city.data,
            state= form.state.data, 
            address= form.address.data, 
            phone= form.phone.data,
            genres=genres,
            image_link= form.image_link.data, 
            facebook_link= form.facebook_link.data, 
            website= form.website_link.data, 
            seeking_talent= form.seeking_talent.data,
            seeking_description= form.seeking_description.data 
        )
        # Add venue to the database session
        db.session.add(venue)
        # Commit changes to the database
        db.session.commit()
        # Store venue data for further use (optional)
        data['venue'] = venue
        # Flash success message
        flash('Venue ' + form.name.data + ' was successfully listed!')
    except Exception as e:
      # Handle errors by rolling back changes and displaying an error message
      flash('An error occurred. Venue ' + form.name.data + str(e) + '. could not be listed.')
      db.session.rollback()
    finally:
      # Close the session
      db.session.close()
    return render_template('pages/home.html')
  else:
    message = []
    for field, errors in form.errors.items():
        for error in errors:
            message.append(f"{field}: {error}")
    flash('Please fix the following errors: ' + ', '.join(message))
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)

@app.route('/venues/<venue_id>/delete', methods=['GET'])
def delete_venue(venue_id):
  # Retrieve venue from the database based on venue_id
  venue = Venue.query.filter_by(id=venue_id).first()
  try:
    # Delete the venue from the database
    db.session.delete(venue)
    # Commit changes to the database
    db.session.commit()
    # Flash success message
    flash('Venue was successfully deleted!')
  except:
    # Handle errors by rolling back changes and displaying an error message
    flash('An error occurred, could not be deleted.')
    db.session.rollback()
  finally:
    db.session.close()
  return render_template('pages/home.html')

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  # Fetch all artists from the database
  artists = Artist.query.all()
  data = []
  # Iterate over each artist and format their information
  for artist in artists:
    data.append({
      "id": artist.id,
      "name": artist.name,
    })
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  # Retrieve the search term from the form submission
  search_term = request.form.get('search_term')
  # Query the database for artists matching the search term
  artists = Artist.query.filter(Artist.name.ilike(f"%{search_term}%")).all()
  # Get the current time
  now = datetime.now()
  # Calculate the number of artists found
  len_artist = len(artists)
  # Initialize a response object
  response = SearchResponse(count=len_artist,data=[])
  # Iterate over each artist and format their information
  for artist in artists:
    # Calculate the number of upcoming shows for the artist
    num_upcoming_shows = sum(1 for show in artist.shows if show.start_time >= now)
    # Append the formatted artist data to the response data list
    response.data.append(SearchData(id=artist.id,name=artist.name,num_upcoming_shows = num_upcoming_shows))
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # Fetch artist from the database based on the artist_id
  artist = Artist.query.filter_by(id = artist_id).first()
  genres_names = [genre.name for genre in artist.genres] 
  now = datetime.now()
  # Initialize lists for past and upcoming shows
  past_shows = []
  upcoming_shows = []
  # Retrieve shows associated with the artist
  for show in artist.shows:
    
    show_dict = {
          "venue_id": show.venue_id,
          "venue_name": show.venue.name,
          "venue_image_link": show.venue.image_link,
          "start_time": show.start_time.strftime("%m/%d/%Y, %H:%M")
    }
    # Determine if the show is past or upcoming and add it to the respective list
    if show.start_time >= now:
      upcoming_shows.append(show_dict)
    else:
      past_shows.append(show_dict)
  # Create a DataDetail object containing artist information, past shows, upcoming shows, and genres
  data = DataDetail(data= artist,past_shows = past_shows,upcoming_shows=upcoming_shows,genres=genres_names)
  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  # Query the artist from the database based on the artist_id
  artist = Artist.query.filter_by(id = artist_id).first()
  # List name of genres
  genres = [ genre.name for genre in artist.genres ]
  # Data artist 
  artist_data = {
    "id": artist_id,
    "name": artist.name,
    "genres": genres,
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "website": artist.website,
    "facebook_link": artist.facebook_link,
    "seeking_venue": artist.seeking_venue,
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link
  }
  # Create an instance of the ArtistForm class, passing the artist data as initial data
  form = ArtistForm(data=artist_data)
  return render_template('forms/edit_artist.html', form=form, artist=artist_data)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # Query the genres selected for the artist from the form data
  genres = Genre.query.filter(Genre.name.in_(request.form.getlist('genres'))).all()
  # Query the artist based on the provided artist_id
  artist = Artist.query.filter_by(id = artist_id).first()
  try:
    # Update the artist's attributes with new values from the form data
    artist.name = request.form.get('name'),
    artist.city = request.form.get('city'),
    artist.state = request.form.get('state'),
    artist.phone = request.form.get('phone'),
    artist.image_link = request.form.get('image_link'),
    artist.facebook_link = request.form.get('facebook_link'),
    artist.website = request.form.get('website'),
    artist.seeking_venue = True if request.form.get('seeking_venue') == 'True' else False
    artist.seeking_description = request.form.get('seeking_description'),
    artist.genres = genres
    # Commit the changes to the database
    db.session.commit()
    # Flash a success message
    flash('Artist ' + request.form.get('name') + ' was successfully edited!')
  except:
    # Handle error
    flash('An error occurred. Artist ' + request.form.get('name') + ' could not be edited.')
    db.session.rollback()
  finally:
    # Close the session
    db.session.close()
  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  # Fetch venue from the database based on venue_id
  venue = Venue.query.filter_by(id = venue_id).first()
  # Extract genres associated with the venue
  genres = [ genre.name for genre in venue.genres ]
  venue_data = {
    "id": venue.id,
    "name": venue.name,
    "genres": genres,
    "address": venue.address,
    "city": venue.city,
    "state": venue.state,
    "phone": venue.phone,
    "website": venue.website,
    "facebook_link": venue.facebook_link,
    "seeking_talent": str(venue.seeking_talent),
    "seeking_description": venue.seeking_description,
    "image_link": venue.image_link
  }
  # Create VenueForm instance with venue data
  form = VenueForm(data=venue_data)
  return render_template('forms/edit_venue.html', form=form, venue=venue_data)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # Extract genres from the form data
  genres = Genre.query.filter(Genre.name.in_(request.form.getlist('genres'))).all()
  # Fetch the venue from the database based on venue_id
  venue = Venue.query.filter_by(id = venue_id).first()
  # Update venue information with form data
  venue.name = request.form.get('name'),
  venue.city = request.form.get('city'),
  venue.state = request.form.get('state'),
  venue.phone = request.form.get('phone'),
  venue.image_link = request.form.get('image_link'),
  venue.facebook_link = request.form.get('facebook_link'),
  venue.website = request.form.get('website'),
  venue.seeking_talent = True if request.form.get('seeking_talent') == 'True' else False
  venue.seeking_description = request.form.get('seeking_description'),
  venue.genres = genres
  try:
    # Commit changes to the database
    db.session.commit()
    # Flash success message
    flash('Venue ' + request.form.get('name') + ' was successfully edited!')
  except:
    # handle error
    flash('An error occurred. Venue ' + request.form.get('name') + ' could not be edited.')
    db.session.rollback()
  finally:
    db.session.close()
  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  #Insert form data as a new Venue record in the db, instead
  data = {}
  form = ArtistForm(request.form, meta={"csrf": False})
  genres = Genre.query.filter(Genre.name.in_(form.genres.data)).all()
  if form.validate():
    artist = Artist(
        name = form.name.data,
        city = form.city.data,
        state = form.state.data,
        genres = genres,
        phone = form.phone.data,
        image_link = form.image_link.data,
        facebook_link = form.facebook_link.data,
        website = form.website_link.data,
        seeking_venue = form.seeking_venue.data,
        seeking_description = form.seeking_description.data,
      )
    try:
      # Add and commit data
      db.session.add(artist)
      db.session.commit()
      # Modify data to be the data object returned from db insertion
      data['artist'] = artist
      # on successful db insert, flash success
      flash('Artist ' + form.name.data + ' was successfully listed!')
    except Exception as e:
      flash('An error occurred. Artist ' + form.name.data + ' could not be listed. ' + str(e))
      db.session.rollback()
    finally:
      db.session.close()
    return render_template('pages/home.html')
  else:
    message = []
    for field, errors in form.errors.items():
        for error in errors:
            message.append(f"{field}: {error}")
    flash('Please fix the following errors: ' + ', '.join(message))
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


#  Shows
#  ----------------------------------------------------------------
@app.route('/shows')
def shows():
  # Execute a query to retrieve all shows along with venue and artist information
  respone = db.session.query(Show, Venue, Artist).\
    join(Venue, Venue.id == Show.venue_id).\
    join(Artist, Artist.id == Show.artist_id).\
    all()
  print(respone)
  data = []
  for show, venue, artist in respone:
    # show data
    show_data = {
        "venue_id": venue.id,
        "venue_name": venue.name,
        "artist_id": artist.id,
        "artist_name": artist.name,
        "artist_image_link": artist.image_link,
        "start_time": str(show.start_time)
    }
    # Append show data to the list
    data.append(show_data)
  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # Retrieve data from the form
  form = ShowForm(request.form,meta={"csrf": False})
  venue_id = form.venue_id.data
  artist_id = form.artist_id.data
  start_time = form.start_time.data
  if form.validate():
    show = Show(
      venue_id=venue_id,
      artist_id=artist_id,
      start_time=start_time
    )
    try:
      # Add and commit data
      db.session.add(show)
      db.session.commit()
      # on successful db insert, flash success
      flash('Show was successfully listed!')
    except Exception as e:
      flash('An error occurred. Show could not be listed. ' + str(e))
      db.session.rollback()
    finally:
      db.session.close()
    return render_template('pages/home.html')
  else:
    message = []
    for field, errors in form.errors.items():
        for error in errors:
            message.append(f"{field}: {error}")
    flash('Please fix the following errors: ' + ', '.join(message))
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
