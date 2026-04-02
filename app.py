import os
import time
import subprocess
import threading
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import yt_dlp
import imageio_ffmpeg

app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)

TMP_DIR = 'tmp'
os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs('public', exist_ok=True)

# Function to delete files after a delay
def remove_file_delayed(path, delay=10):
    def delayed_delete():
        time.sleep(delay)
        try:
            if os.path.exists(path):
                os.remove(path)
                print(f"Deleted temp file: {path}")
        except Exception as e:
            print(f"Failed to delete {path}: {e}")
    threading.Thread(target=delayed_delete).start()

@app.route('/')
def serve_index():
    return app.send_static_file('index.html')

@app.route('/download', methods=['GET'])
def download():
    url = request.args.get('url')
    type = request.args.get('type')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    file_id = str(int(time.time() * 1000))
    is_audio = type == 'audio'
    
    outtmpl_path = os.path.join(TMP_DIR, f"{file_id}.%(ext)s")
    
    # Use imageio_ffmpeg to get the ffmpeg binary so the user doesn't need to install it locally
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    
    ydl_opts = {
        'outtmpl': outtmpl_path,
        'quiet': False,
        'no_warnings': True,
        'ffmpeg_location': ffmpeg_path,
    }
    
    if is_audio:
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    else:
        # Windowsの標準プレイヤーで再生できるように、AV1/VP9ではなくH.264（avc）コーデックを優先して取得します
        ydl_opts['format'] = 'bestvideo[ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]/best[ext=mp4][vcodec^=avc]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        ydl_opts['merge_output_format'] = 'mp4'

    print(f"Starting download for: {url}")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        # Find the final downloaded file
        final_output_path = None
        final_ext = ''
        for f in os.listdir(TMP_DIR):
            if f.startswith(file_id):
                final_output_path = os.path.join(TMP_DIR, f)
                final_ext = f.split('.')[-1]
                break
                
        if not final_output_path:
            raise Exception("Downloaded file not found in tmp directory.")
            
        print(f"Download complete: {final_output_path}")
        
        # Schedule cleanup after sending the file
        remove_file_delayed(final_output_path, delay=30)
            
        return send_file(
            final_output_path, 
            as_attachment=True, 
            download_name=f"youtube_{file_id}.{final_ext}"
        )
        
    except Exception as e:
        print(f"Download Error: {str(e)}")
        return jsonify({'error': 'Failed to download media', 'details': str(e)}), 500

if __name__ == '__main__':
    print("Starting server on http://localhost:3000")
    app.run(port=3000, debug=True)
