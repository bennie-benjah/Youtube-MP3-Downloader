from flask import Flask, render_template, request, jsonify, Response, send_file
import yt_dlp as youtube_dl
import os
import json

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

progress_data = ""

@app.route('/')
def index():
    return render_template('index.html')
def progress_hook(progress):
    # The line `global progress_data` is declaring that the variable `progress_data` inside the
    # `progress_hook` function is referring to the global variable `progress_data` defined outside the
    # function. This allows the function to modify the global variable `progress_data` instead of
    # creating a new local variable with the same name. This way, changes made to `progress_data`
    # inside the function will affect the global variable `progress_data` outside the function as
    # well.
    global progress_data
    if progress['status'] == 'downloading':
        # Extract the numeric part of the progress percentage string
        percentage_str = progress['_percent_str'].split('%')[0]
        try:
            percentage = float(percentage_str)
        except ValueError:
            # Handle cases where conversion to float fails
            percentage = 0.0  # Default value if conversion fails
        speed = progress['_speed_str']
        eta = progress['_eta_str']
        progress_data = {'status': 'downloading', 'percentage': percentage, 'speed': speed, 'eta': eta}
    elif progress['status'] == 'finished':
        progress_data = {'status': 'finished', 'message': 'Download complete.'}

@app.route('/progress')
def progress():
    url = request.args.get('url')
    if url:
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'progress_hooks': [progress_hook],
        }

        def generate_progress():
            global progress_data
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=False)
                while 'status' not in progress_data or progress_data['status'] != 'finished':
                    yield f'data: {json.dumps(progress_data)}\n\n'

        return Response(generate_progress(), content_type='text/event-stream')
    else:
        return jsonify({'error': 'Missing URL parameter'}), 400

@app.route('/download', methods=['POST'])
def download():
    url = request.form['url']
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(os.path.expanduser('~'), 'Downloads', '%(title)s.%(ext)s'),
            'progress_hooks': [progress_hook],
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            video_title = info_dict.get('title', None)
            mp3_filename = os.path.join(os.path.expanduser('~'), 'Downloads', f"{video_title}.mp3")

            return jsonify({'success': True, 'filename': mp3_filename})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/download_file')
def download_file():
    filename = request.args.get('filename')
    if filename:
        return send_file(filename, as_attachment=True)
    else:
        return jsonify({'error': 'Missing filename parameter'}), 400

if __name__ == '__main__':
    app.run(debug=True)
