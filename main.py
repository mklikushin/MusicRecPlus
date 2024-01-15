#Gets the user tracks

import requests
from flask import Flask, redirect, request, jsonify, session, url_for
from datetime import datetime
import urllib.parse
import json
import os
from dotenv import dotenv_values

import spotipy
from spotipy.oauth2 import SpotifyOAuth

#http://localhost:5000/

app = Flask(__name__)

script_directory = os.path.dirname(os.path.abspath(__file__))   #directory path
env_id_file_path = os.path.join(script_directory, '.env.id')        #client id env file
env_secret_file_path = os.path.join(script_directory,'.env.secret') #secret env file

config = {
    **dotenv_values(env_id_file_path),
    **dotenv_values(env_secret_file_path)
}

app.secret_key = config['SECRET_KEY']
client_id = config['CLIENT_ID']
client_secret = config['CLIENT_SECRET']

redirect_uri = 'http://localhost:5000/callback'

AUTH_URL = 'https://accounts.spotify.com/authorize'
token_url = 'https://accounts.spotify.com/api/token'
API_base_url = 'https://api.spotify.com/v1/'


@app.route('/')
def index():
    return "Fuck you: <a href='/login'>Login with Spotify</a>"   #This is the button to login where we redirect to them our endpoint

@app.route('/login')
def login():
    scope = 'user-read-private user-read-email' #private playlists and email
    params = {
        'client_id' : client_id,
        'response_type' : 'code',
        'scope' : scope,
        'redirect_uri': redirect_uri,
        'show_dialog': True             #NEED THIS TO LOG IN
    }
    
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)
    
    
    
@app.route('/callback')
def callback():
    #Check for error
    if 'error' in request.args:
        return jsonify({'error': request.args['error']})
    
    if 'code' in request.args:
        
        data = {
            'code' : request.args['code'],       #This is the code they sent us
            'grant_type': 'authorization_code',  
            'redirect_uri': redirect_uri,       
            'client_id': client_id,
            'client_secret': client_secret             
        }
        
        response = requests.post(url=token_url, data=data)
        token_info = response.json() #Comes as json object
        
        if 'error' in token_info:
            return jsonify({'error': token_info['error']})
        
        session['access_token'] = token_info['access_token']
        session['refresh_token'] = token_info['refresh_token']
        session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']     #Lasts one hour. Just get the time and add the time it expires.
        
        return redirect('/tracks')    
        
        
        
@app.route('/tracks') 
def get_tracks():
    #refresh if expired
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh_token') 
    
    #CLIENT = spotipy.Spotify(auth=session['access_token']) #only need access token 
    
    scope = 'playlist-read-private playlist-read-collaborative user-library-read'
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope=scope))
    
    All_Playlist_json = sp.current_user_playlists() 
    All_Playlists = All_Playlist_json['items'] #get playlist
    
    Items = []
    
    for i in All_Playlists:
        playlist_id = i['id']       #gets id from playlist i
        total_tracks = i['tracks']['total']
        offset = 0
        
        while offset < total_tracks:        #limit is 100 for each retrieval
            tracks_data = sp.playlist_tracks(playlist_id, offset=offset)    #JSON array of every track
            for j in tracks_data['items']:
                if isinstance(j, dict) and 'track' in j and isinstance(j['track'], dict):
                    track_name = j['track']['name']
                    Items.append(track_name)
           
            offset += len(tracks_data['items'])
            
    #Items = [track.replace("\\","") for track in Items]
    #Songs in other languages will needed to be printed
    return Items


@app.route('/refresh_token')
def refresh_token():
    if 'refresh_token' not in session:
        return redirect('/login')

    #refresh token if it expired
    if datetime.now().timestamp() > session['expires_at']:    
        request_body = {
            'grant_type' : 'refresh_token',
            'refresh_token' : session['refresh_token'],
            'client_id' : client_id,
            'client_secret' : client_secret
        }    
        
        response = requests.post(token_url, data=request_body)
        new_token_info = response.json()
        
        session['access_token'] = new_token_info['access_token']
        session['expires_at'] = datetime.now().timestamp() + new_token_info['expires_in']
        
        return redirect('/tracks')    



if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)