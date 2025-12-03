import os
import sys
import shutil
import json
import hashlib
import threading

# Remove instalação automática de dependências (já vem no APK)
# As dependências são instaladas pelo buildozer

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.uix.togglebutton import ToggleButton
from kivy.clock import Clock
from kivy.core.window import Window

# Configurações para mobile
Window.keyboard_anim_args = {'d': 0.2, 't': 'in_out_expo'}
Window.softinput_mode = "below_target"

def verificar_ffmpeg():
    """Verifica se o FFmpeg está instalado no sistema"""
    return shutil.which("ffmpeg") is not None

def obter_caminho_base():
    """Retorna o caminho base onde o script está localizado"""
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    
    script_path = os.path.dirname(os.path.abspath(__file__))
    return script_path

def criar_estrutura_pastas():
    """Cria a estrutura de pastas assets/playlists e assets/cache"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.join(script_dir, 'YouTubeDownloader')
    
    # Em Android, tenta usar storage externo se disponível
    try:
        from android.storage import primary_external_storage_path
        from android.permissions import request_permissions, Permission
        request_permissions([
            Permission.WRITE_EXTERNAL_STORAGE, 
            Permission.READ_EXTERNAL_STORAGE,
            Permission.INTERNET
        ])
        
        storage_path = primary_external_storage_path()
        base_dir = os.path.join(storage_path, 'YouTubeDownloader')
    except:
        pass
    
    pastas = [
        base_dir,
        os.path.join(base_dir, 'playlists'),
        os.path.join(base_dir, 'cache', 'musicas'),
        os.path.join(base_dir, 'cache', 'videos_individuais_mp3'),
        os.path.join(base_dir, 'cache', 'videos_individuais_mp4')
    ]
    
    for pasta in pastas:
        try:
            if not os.path.exists(pasta):
                os.makedirs(pasta)
        except Exception as e:
            print(f"Erro ao criar pasta {pasta}: {e}")
    
    return base_dir

def carregar_cache():
    """Carrega o arquivo JSON com o histórico de downloads"""
    try:
        base_path = criar_estrutura_pastas()
        cache_file = os.path.join(base_path, 'cache', 'downloaded_tracks.json')
        
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Erro ao carregar cache: {e}")
    
    return {}

def salvar_cache(cache):
    """Salva o cache atualizado no arquivo JSON"""
    try:
        base_path = criar_estrutura_pastas()
        cache_file = os.path.join(base_path, 'cache', 'downloaded_tracks.json')
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar cache: {e}")

def gerar_id_video(url_ou_id, formato='mp3'):
    """Gera um ID único para o vídeo incluindo o formato"""
    return hashlib.md5(f"{url_ou_id}_{formato}".encode()).hexdigest()

def sanitizar_nome_arquivo(nome):
    """Remove caracteres inválidos do nome do arquivo"""
    caracteres_invalidos = '<>:"/\\|?*'
    for char in caracteres_invalidos:
        nome = nome.replace(char, '_')
    return nome

def detectar_tipo_url(url):
    """Detecta se a URL é de uma playlist, vídeo individual ou clip"""
    try:
        import yt_dlp
    except ImportError:
        return None, "yt-dlp não está instalado"
    
    if '/clip/' in url:
        try:
            ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': False}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    return 'clip', info
        except Exception as e:
            return None, f"Erro ao acessar clip: {str(e)[:100]}"
    
    ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': True}
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if 'entries' in info and info.get('_type') == 'playlist':
                playlist_id = info.get('id', '')
                if playlist_id.startswith('RD') or playlist_id.startswith('UL'):
                    return 'video', info.get('entries', [{}])[0] if info.get('entries') else info
                return 'playlist', info
            else:
                return 'video', info
                
    except Exception as e:
        error_msg = str(e)
        if 'unavailable' in error_msg.lower():
            return None, "Vídeo indisponível"
        elif 'private' in error_msg.lower():
            return None, "Vídeo privado"
        else:
            return None, f"Erro: {error_msg[:100]}"

def obter_info_playlist(playlist_url):
    """Obtém informações sobre os vídeos da playlist"""
    try:
        import yt_dlp
        
        ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': True}
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            return info.get('entries', [])
    except Exception as e:
        print(f"Erro ao obter playlist: {e}")
        return []

def copiar_do_cache(video_hash, video_title, output_path, cache):
    """Copia uma música do cache para a pasta da playlist"""
    try:
        cache_info = cache.get(video_hash)
        if not cache_info:
            return False
        
        arquivo_cache = cache_info.get('arquivo_cache')
        if not arquivo_cache or not os.path.exists(arquivo_cache):
            return False
        
        _, ext = os.path.splitext(arquivo_cache)
        nome_sanitizado = sanitizar_nome_arquivo(video_title)
        arquivo_destino = os.path.join(output_path, f"{nome_sanitizado}{ext}")
        
        shutil.copy2(arquivo_cache, arquivo_destino)
        return True
        
    except Exception as e:
        print(f"Erro ao copiar do cache: {e}")
        return False

def download_para_cache(video_id, video_title, video_hash, cache, ffmpeg_disponivel, is_individual=False, formato_video='mp3'):
    """Baixa uma música/vídeo diretamente para o cache"""
    try:
        import yt_dlp
    except ImportError:
        return False, "yt-dlp não está disponível"
    
    try:
        base_path = criar_estrutura_pastas()
        
        if is_individual:
            if formato_video == 'mp4':
                cache_path = os.path.join(base_path, 'cache', 'videos_individuais_mp4')
                tipo = 'individual_mp4'
                formato = 'mp4'
            else:
                cache_path = os.path.join(base_path, 'cache', 'videos_individuais_mp3')
                tipo = 'individual_mp3'
                formato = 'mp3' if ffmpeg_disponivel else 'm4a'
        else:
            cache_path = os.path.join(base_path, 'cache', 'musicas')
            tipo = 'playlist'
            formato = 'mp3' if ffmpeg_disponivel else 'm4a'
        
        nome_arquivo = f"{video_hash}.{formato}"
        arquivo_cache = os.path.join(cache_path, nome_arquivo)
        
        opcoes_comuns = {
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'user_agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36',
            'referer': 'https://www.youtube.com/',
        }
        
        if formato_video == 'mp4' and is_individual:
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': arquivo_cache,
                **opcoes_comuns
            }
        elif ffmpeg_disponivel and formato_video == 'mp3':
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.join(cache_path, f"{video_hash}.%(ext)s"),
                **opcoes_comuns
            }
        else:
            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio',
                'outtmpl': arquivo_cache,
                **opcoes_comuns
            }
        
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        cache[video_hash] = {
            'id': video_id,
            'title': video_title,
            'formato': formato,
            'arquivo_cache': arquivo_cache,
            'tipo': tipo
        }
        
        salvar_cache(cache)
        return True, None
        
    except Exception as e:
        erro_str = str(e)
        if '403' in erro_str or 'forbidden' in erro_str.lower():
            return False, "Erro 403: Atualize o yt-dlp"
        return False, f"Erro: {erro_str[:100]}"


class YouTubeDownloaderApp(App):
    def build(self):
        self.title = 'YouTube Downloader'
        
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        title = Label(text='[b]YouTube Downloader[/b]', 
                     markup=True, 
                     size_hint_y=None, 
                     height=50,
                     font_size='20sp')
        layout.add_widget(title)
        
        url_label = Label(text='URL (Playlist, Vídeo ou Clip):', 
                         size_hint_y=None, 
                         height=30,
                         font_size='14sp')
        layout.add_widget(url_label)
        
        self.url_input = TextInput(hint_text='Cole a URL aqui',
                                   multiline=False,
                                   size_hint_y=None,
                                   height=50,
                                   font_size='14sp')
        layout.add_widget(self.url_input)
        
        nome_label = Label(text='Nome da Playlist:', 
                          size_hint_y=None, 
                          height=30,
                          font_size='14sp')
        layout.add_widget(nome_label)
        
        self.nome_input = TextInput(text='minha_playlist',
                                   multiline=False,
                                   size_hint_y=None,
                                   height=50,
                                   font_size='14sp')
        layout.add_widget(self.nome_input)
        
        formato_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        formato_label = Label(text='Formato (vídeos):', font_size='14sp')
        formato_layout.add_widget(formato_label)
        
        self.btn_mp3 = ToggleButton(text='MP3', group='formato', state='down')
        self.btn_mp4 = ToggleButton(text='MP4', group='formato')
        formato_layout.add_widget(self.btn_mp3)
        formato_layout.add_widget(self.btn_mp4)
        layout.add_widget(formato_layout)
        
        self.download_btn = Button(text='Iniciar Download',
                                  size_hint_y=None,
                                  height=60,
                                  background_color=(0.2, 0.6, 1, 1),
                                  font_size='16sp')
        self.download_btn.bind(on_press=self.iniciar_download)
        layout.add_widget(self.download_btn)
        
        self.progress = ProgressBar(max=100, 
                                   size_hint_y=None, 
                                   height=30)
        layout.add_widget(self.progress)
        
        self.status_label = Label(text='Aguardando...', 
                                 size_hint_y=None, 
                                 height=30,
                                 font_size='12sp')
        layout.add_widget(self.status_label)
        
        log_scroll = ScrollView(size_hint=(1, 1))
        self.log_label = Label(text='',
                              size_hint_y=None,
                              font_size='11sp',
                              markup=True,
                              halign='left',
                              valign='top')
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        log_scroll.add_widget(self.log_label)
        layout.add_widget(log_scroll)
        
        cache = carregar_cache()
        mp3_ind = sum(1 for v in cache.values() if v.get('tipo') == 'individual_mp3')
        mp4_ind = sum(1 for v in cache.values() if v.get('tipo') == 'individual_mp4')
        playlists = sum(1 for v in cache.values() if v.get('tipo') == 'playlist')
        
        self.cache_label = Label(
            text=f'Cache: {len(cache)} itens | MP3: {mp3_ind+playlists} | MP4: {mp4_ind}',
            size_hint_y=None,
            height=30,
            font_size='11sp',
            color=(0.5, 0.5, 1, 1))
        layout.add_widget(self.cache_label)
        
        self.log('[b]YouTube Downloader v2.0[/b]')
        self.log('Sistema pronto!\n')
        
        return layout
    
    def log(self, mensagem):
        Clock.schedule_once(lambda dt: self._log_ui(mensagem))
    
    def _log_ui(self, mensagem):
        self.log_label.text += mensagem + '\n'
    
    def atualizar_status(self, mensagem):
        Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', mensagem))
    
    def mostrar_popup(self, titulo, mensagem):
        def _show():
            content = BoxLayout(orientation='vertical', padding=10)
            content.add_widget(Label(text=mensagem))
            btn = Button(text='OK', size_hint_y=None, height=50)
            content.add_widget(btn)
            
            popup = Popup(title=titulo, content=content, size_hint=(0.9, 0.5))
            btn.bind(on_press=popup.dismiss)
            popup.open()
        
        Clock.schedule_once(lambda dt: _show())
    
    def iniciar_download(self, instance):
        url = self.url_input.text.strip()
        nome = self.nome_input.text.strip()
        formato = 'mp3' if self.btn_mp3.state == 'down' else 'mp4'
        
        if not url:
            self.mostrar_popup('Atenção', 'Por favor, insira a URL!')
            return
        
        if not url.startswith('http'):
            if url.startswith('www.') or url.startswith('youtube.com') or url.startswith('youtu.be'):
                url = 'https://' + url
        
        if '?list=RD' in url or '&list=RD' in url:
            import re
            video_match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
            if video_match:
                video_id = video_match.group(1)
                url = f'https://www.youtube.com/watch?v={video_id}'
                self.log('[color=ffaa00]Playlist automática detectada - usando vídeo individual[/color]')
        
        self.download_btn.disabled = True
        self.atualizar_status('Processando...')
        
        thread = threading.Thread(target=self.processar_download, args=(url, nome, formato))
        thread.daemon = True
        thread.start()
    
    def processar_download(self, url, nome, formato):
        try:
            self.log('\n[b]Detectando tipo...[/b]')
            tipo, info = detectar_tipo_url(url)
            
            if tipo is None:
                erro = info if isinstance(info, str) else "Erro ao acessar"
                self.log(f'[color=ff0000]{erro}[/color]')
                self.atualizar_status('Erro')
                self.mostrar_popup('Erro', erro)
                return
            
            if tipo == 'playlist':
                self.log(f'[color=00ff00]Playlist detectada[/color]')
                self.log(f'Título: {info.get("title", "N/A")}')
                self.download_playlist(url, nome)
            else:
                self.log(f'[color=00ff00]Vídeo individual detectado[/color]')
                self.log(f'Título: {info.get("title", "N/A")}')
                self.download_video(url, info, formato)
                
        except Exception as e:
            self.log(f'[color=ff0000]Erro: {str(e)}[/color]')
            self.mostrar_popup('Erro', str(e))
        finally:
            Clock.schedule_once(lambda dt: setattr(self.download_btn, 'disabled', False))
            Clock.schedule_once(lambda dt: setattr(self.progress, 'value', 0))
    
    def download_video(self, url, info, formato):
        base_path = criar_estrutura_pastas()
        cache = carregar_cache()
        
        video_id = info.get('id', '')
        video_title = info.get('title', 'Sem título')
        video_hash = gerar_id_video(video_id, formato)
        ffmpeg_disponivel = verificar_ffmpeg()
        
        Clock.schedule_once(lambda dt: setattr(self.progress, 'max', 1))
        
        if video_hash in cache:
            arquivo = cache[video_hash].get('arquivo_cache')
            if arquivo and os.path.exists(arquivo):
                self.log('[color=00ff00]Já está no cache![/color]')
                self.mostrar_popup('Sucesso', f'Arquivo já baixado!\n\n{arquivo}')
                Clock.schedule_once(lambda dt: setattr(self.progress, 'value', 1))
                return
        
        self.log('Baixando...')
        sucesso, erro = download_para_cache(video_id, video_title, video_hash, cache, ffmpeg_disponivel, True, formato)
        
        if sucesso:
            arquivo = cache[video_hash].get('arquivo_cache')
            self.log(f'[color=00ff00]Sucesso![/color]\n{arquivo}')
            self.mostrar_popup('Sucesso', f'Download concluído!\n\n{arquivo}')
            Clock.schedule_once(lambda dt: setattr(self.progress, 'value', 1))
        else:
            self.log(f'[color=ff0000]{erro}[/color]')
            self.mostrar_popup('Erro', erro)
    
    def download_playlist(self, url, nome):
        base_path = criar_estrutura_pastas()
        output_path = os.path.join(base_path, 'playlists', nome)
        
        try:
            if not os.path.exists(output_path):
                os.makedirs(output_path)
        except Exception as e:
            self.log(f'[color=ff0000]Erro ao criar pasta: {e}[/color]')
            return
        
        cache = carregar_cache()
        ffmpeg_disponivel = verificar_ffmpeg()
        
        videos = obter_info_playlist(url)
        if not videos:
            self.log('[color=ff0000]Erro ao obter playlist[/color]')
            return
        
        self.log(f'Encontrados {len(videos)} vídeos\n')
        Clock.schedule_once(lambda dt: setattr(self.progress, 'max', len(videos)))
        
        copiados = baixados = erros = 0
        
        for i, video in enumerate(videos, 1):
            if not video:
                continue
            
            video_id = video.get('id', '')
            video_title = video.get('title', 'Sem título')
            video_hash = gerar_id_video(video_id, 'mp3')
            
            self.log(f'[{i}/{len(videos)}] {video_title[:40]}...')
            Clock.schedule_once(lambda dt, v=i: setattr(self.progress, 'value', v))
            
            if video_hash in cache:
                if copiar_do_cache(video_hash, video_title, output_path, cache):
                    copiados += 1
                    continue
            
            sucesso, erro = download_para_cache(video_id, video_title, video_hash, cache, ffmpeg_disponivel, False)
            if sucesso:
                if copiar_do_cache(video_hash, video_title, output_path, cache):
                    baixados += 1
                else:
                    erros += 1
            else:
                erros += 1
        
        self.log(f'\n[color=00ff00]Concluído![/color]')
        self.log(f'Copiados: {copiados} | Baixados: {baixados} | Erros: {erros}')
        self.mostrar_popup('Concluído', f'Copiados: {copiados}\nBaixados: {baixados}\nErros: {erros}')


if __name__ == '__main__':
    YouTubeDownloaderApp().run()
