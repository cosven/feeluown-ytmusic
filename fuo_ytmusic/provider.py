from typing import List, Optional

from feeluown.excs import NoUserLoggedIn
from feeluown.library import AbstractProvider, ProviderV2, ModelType, ProviderFlags as Pf, SongModel, BriefVideoModel, \
    BriefUserModel
from feeluown.media import Quality, Media, VideoAudioManifest, MediaType
from feeluown.models import SearchType, SearchModel, PlaylistModel, ArtistModel
from feeluown.library.model_protocol import BriefSongProtocol

from fuo_ytmusic.consts import HEADER_FILE
from fuo_ytmusic.models import YtmusicPlaylistModel, Categories
from fuo_ytmusic.service import YtmusicService, YtmusicType


class YtmusicProvider(AbstractProvider, ProviderV2):
    service: YtmusicService

    def __init__(self):
        super(YtmusicProvider, self).__init__()
        self.service: YtmusicService = YtmusicService()
        self._user = None

    # noinspection PyPep8Naming
    class meta:
        identifier = 'ytmusic'
        name = 'YouTube Music'
        flags = {
            ModelType.song: (Pf.model_v2 | Pf.multi_quality | Pf.mv | Pf.lyric),
            ModelType.video: Pf.multi_quality,
        }

    @property
    def identifier(self):
        return self.meta.identifier

    @property
    def name(self):
        return self.meta.name

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self.service.setup()
        self._user = user

    def library_songs(self):
        songs = self.service.library_songs(100)
        return [song.model() for song in songs]

    def library_albums(self):
        albums = self.service.library_albums(100)
        return [album.model() for album in albums]

    def library_artists(self) -> List[ArtistModel]:
        artists = self.service.library_subscription_artists(100)
        return [artist.model() for artist in artists]

    def library_playlists(self) -> List[YtmusicPlaylistModel]:
        playlists = self.service.library_playlists(100)
        return [playlist.model(self) for playlist in playlists]

    def playlist_info(self, identifier) -> YtmusicPlaylistModel:
        return self.service.playlist_info(identifier, limit=20).model()

    def categories(self) -> Categories:
        return self.service.categories()

    def user_from_cookie(self, _):
        return BriefUserModel(identifier='', source=self.meta.identifier, name='Me')

    def has_current_user(self) -> bool:
        return HEADER_FILE.exists()

    def get_current_user(self):
        if not HEADER_FILE.exists():
            raise NoUserLoggedIn
        return BriefUserModel(identifier='', source=self.meta.identifier, name='Me')

    def user_get(self, identifier):
        if identifier is None:
            return None
        if identifier == '':
            return BriefUserModel(identifier='', source=self.meta.identifier, name='Me')
        user = self.service.user_info(identifier)
        return BriefUserModel(identifier=identifier, source=self.meta.identifier, name=user.name)

    def search(self, keyword, type_, *args, **kwargs):
        type_ = SearchType.parse(type_)
        ytmusic_type = YtmusicType.parse(type_)
        results = self.service.search(keyword, ytmusic_type)
        model = SearchModel(q=keyword)
        setattr(model, ytmusic_type.value, [r.model() for r in results])
        return model

    def song_list_quality(self, song) -> List[Quality.Audio]:
        id_ = song.identifier
        song_ = self.service.song_info(id_)
        return song_.list_formats() if song_ is not None else []

    def song_get_media(self, song: SongModel, quality: Quality.Audio) -> Optional[Media]:
        song_info = self.service.song_info(song.identifier)
        format_code, bitrate, format_str = song_info.get_media(quality)
        url = self.service.stream_url(song.identifier, format_code)
        return Media(url, type_=MediaType.audio, bitrate=bitrate, format=format_str) if url is not None else None

    def song_get_lyric(self, song):
        # 歌词获取报错的 workaround
        return None

    def video_list_quality(self, video) -> List[Quality.Video]:
        id_ = video.identifier
        song_ = self.service.song_info(id_)
        return song_.list_video_formats() if song_ is not None else []

    def video_get_media(self, video, quality) -> Optional[Media]:
        song_info = self.service.song_info(video.identifier)
        format_code = song_info.get_mv(quality)
        audio_formats = song_info.list_formats()
        audio_code, _, __ = song_info.get_media(audio_formats[0])
        url = self.service.stream_url(video.identifier, format_code)
        audio_url = self.service.stream_url(video.identifier, audio_code)
        if url is None or audio_url is None:
            return None
        return Media(VideoAudioManifest(url, audio_url))

    def song_get_mv(self, song: BriefSongProtocol) -> BriefVideoModel:
        return BriefVideoModel(identifier=song.identifier, source=song.source, title=song.title,
                               artists_name=song.artists_name, duration_ms=song.duration_ms)
