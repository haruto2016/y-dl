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
    is_gif = type == 'gif'
    
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
    elif is_gif:
        # GIF変換用：なるべく小さめのファイルサイズをダウンロードして変換を早くする
        ydl_opts['format'] = 'bestvideo[height<=360][ext=mp4]/bestvideo[ext=mp4]/best[ext=mp4]/best'
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
            
        if is_gif:
            gif_output_path = os.path.join(TMP_DIR, f"{file_id}.gif")
            print(f"Converting {final_output_path} to GIF...")
            # Scratch向けの最適化: 解像度240px、10fps、最大60秒
            cmd = [
                ffmpeg_path, '-y', '-i', final_output_path,
                '-t', '60',
                '-vf', 'fps=10,scale=240:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5',
                '-loop', '0',
                gif_output_path
            ]
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                os.remove(final_output_path) # 元の動画を削除
                final_output_path = gif_output_path
                final_ext = 'gif'
                print(f"GIF Conversion complete: {final_output_path}")
            except subprocess.CalledProcessError as e:
                print(f"FFmpeg Error: {e.stderr.decode()}")
                raise Exception("Failed to convert video to GIF.")

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
