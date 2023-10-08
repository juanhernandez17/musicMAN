from fastapi import FastAPI
from dotenv import load_dotenv
from src.musicMAN import musicMAN
from src.monitor.dmx import testARLs
load_dotenv()
app = FastAPI()

if __name__ == "__main__":
	theman = musicMAN()
	theman.refreshLoc()
	# theman.getfiles(['Z:/exHDD/Music'])
	# theman.getCollectionISRCList()
	# theman.dl_missing_tracks()
	# theman.updateSpotifyPlaylist()
	# theman.spotifyPlaylistToM3U()
	# theman.splitExisting(['Z:/exHDD/Music/English','Z:/exHDD/Music/Spanish'],True)
	# theman.updateDeezerPlaylists()
	# theman.dz.getDiscography(13916083)
	# theman.refreshCollect(True)
	# theman.updateDeezerSongs()
	# res = list(theman.dbsp.get_Albums(['5JguPDbzXjKpCQexnYiPNt']))
	# theman.getDeezerDiscography('80365122')
	# theman.addCollection('flac;https://www.deezer.com/artist/5230088')
	# theman.addCollection('flac;https://open.spotify.com/artist/0ys2OFYzWYB5hRDLCsBqxt')
	# theman.updateSongsSP()
	# theman.getDeezerPlaylists()
	# theman.getDeezerLikes()
	# theman.getDeezerPlaylist(8005472302)
	# theman.getDeezerDiscography(13916083)
	# theman.getSpotifyPlaylists()
	# theman.getSpotifyPlaylist('37i9dQZF1DX7V3ptrxki0a')
	# theman.getSpotifyDiscography('0k7Xl1pqI3tu8sSEjo5oEg')
	# theman.getSpotifyLiked()
	# theman.updateSpotifyPlaylists()
	# theman.updateSongsDZ()
	# theman.updateSongsDZ()
	# add_song(tk)
	# get_song('')
	pass