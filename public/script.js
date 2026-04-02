document.addEventListener('DOMContentLoaded', () => {
    const urlInput = document.getElementById('url-input');
    const btnVideo = document.getElementById('btn-video');
    const btnAudio = document.getElementById('btn-audio');
    const btnGif = document.getElementById('btn-gif');
    const errorMsg = document.getElementById('error-msg');
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingText = document.getElementById('loading-text');

    const isValidYoutubeUrl = (url) => {
        const regex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$/;
        return regex.test(url);
    };

    const handleDownload = async (type) => {
        const url = urlInput.value.trim();

        if (!isValidYoutubeUrl(url)) {
            errorMsg.classList.add('visible');
            urlInput.style.borderColor = '#ff4b4b';
            return;
        }

        errorMsg.classList.remove('visible');
        urlInput.style.borderColor = 'rgba(255, 255, 255, 0.1)';
        
        loadingOverlay.classList.remove('hidden');
        
        let loadingTextContent = 'ビデオをダウンロード中...';
        if (type === 'audio') loadingTextContent = '音声を抽出・ダウンロード中...';
        else if (type === 'gif') loadingTextContent = 'Scratch用GIFに変換中 (かなり時間がかかります)...';
        loadingText.textContent = loadingTextContent;

        try {
            const apiUrl = `/download?url=${encodeURIComponent(url)}&type=${type}`;
            
            const response = await fetch(apiUrl);
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Download failed');
            }

            let ext = 'mp4';
            if (type === 'audio') ext = 'mp3';
            else if (type === 'gif') ext = 'gif';
            
            let filename = `youtube_${Date.now()}.${ext}`;
            const disposition = response.headers.get('content-disposition');
            if (disposition && disposition.indexOf('attachment') !== -1) {
                const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                const matches = filenameRegex.exec(disposition);
                if (matches != null && matches[1]) { 
                  filename = matches[1].replace(/['"]/g, '');
                }
            }

            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = downloadUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(downloadUrl);
            a.remove();
            
            urlInput.value = '';

        } catch (err) {
            console.error(err);
            alert(`エラーが発生しました: ${err.message}`);
        } finally {
            loadingOverlay.classList.add('hidden');
        }
    };

    btnVideo.addEventListener('click', () => handleDownload('video'));
    btnAudio.addEventListener('click', () => handleDownload('audio'));
    btnGif.addEventListener('click', () => handleDownload('gif'));
    
    urlInput.addEventListener('input', () => {
        if (errorMsg.classList.contains('visible')) {
            errorMsg.classList.remove('visible');
            urlInput.style.borderColor = 'rgba(255, 255, 255, 0.1)';
        }
    });

    urlInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleDownload('video'); // Default to video on enter
        }
    });
});
