# musicMAN
Python Tool to backup Online Playlist and Discography Data to a mongodb database. Currently works with Spotify and Deezer.

## What can it do?  
Backup Spotify Artist Discography and Playlist Data  
Backup Deezer Artist Discography and Playlist Data  
Scan local files to keep track of a song collection  
Create local .m3u playlist files from the online playlist backups and local files data.  
Use the online backup data and local library to generate a file containing a list of all missing songs from your local library.  
    - format: [ISRC] - [Quality] - [Title]  
    
# Requirements  

## Python 3.11.5  

* requirements.txt
  - deezer-py and deezer-python have conflicting package names so you will have to install them manually
    - install deezer-py first rename it and any references inside the .py files to deezerpy
    - install deezer-python and leave as is

## Mongodb

## .ENV example

### MongoDB Information  
>MONGO='mongodb://localhost:27017'  
### Spotify Information  
>SPOTIFY_CLIENT_ID=''  
>SPOTIFY_CLIENT_SECRET=''

### Deezer Information  
>DEEZERAPPID=''  
>DEEZERSECRET=''  
>DEEZERUSERID=''  
>DEEZERTOKEN = ''  
>DEEZERARL=''  
>DEEZERARLDL=''  