// DOM Elements
const loadingBar = document.getElementById('loading-bar');
const imageContainer = document.getElementById('image-container');
const statusText = document.getElementById('status-text');

/**
 * Updates the loading status text and progress bar
 * @param {string} status - Status message to display (can include HTML)
 * @param {number} progress - Progress value between 0 and 1
 */
function updateLoadingStatus(status, progress) {
    console.log('Updating status:', status);
    // Ensure status text updates are visible
    statusText.classList.remove('active');
    // Force reflow
    void statusText.offsetWidth;
    statusText.innerHTML = status;
    statusText.classList.add('active');
    
    // Update progress
    NProgress.configure({ showSpinner: false });
    NProgress.set(progress);
}

/**
 * Handles the main image generation flow
 */
async function sendMessage() {
    const input = document.getElementById('user-input');
    const message = input.value;
    if (!message) return;

    // Clear everything at the start
    input.value = '';
    imageContainer.innerHTML = '';
    const existingInfo = document.querySelector('.info-and-buttons');
    if (existingInfo) {
        existingInfo.remove();
    }
    
    // Clear any cached data
    window.chatData = null;
    
    try {
        NProgress.configure({ showSpinner: false });
        NProgress.start();
        
        // Step 1: Process GitHub data
        updateLoadingStatus('Collecting data from GitHub for handle <b>' + message + '</b>...', 0.1);
        const chatResponse = await fetch('/chat/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message })
        });

        if (!chatResponse.ok) throw new Error('Chat processing failed');
        const chatData = await chatResponse.json();
        
        if (chatData.status === 'success') {
            // Add debug logging
            console.log('Received chat data:', chatData);
            console.log('Languages:', chatData.languages);
            
            // Store the response for later
            const aiResponse = chatData.response;
            updateLoadingStatus('Received AI response...', 0.4);
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Step 2: Generate image
            updateLoadingStatus('Sending request to DALL-E API...', 0.6);
            const imageResponse = await fetch('/chat/generate-image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: aiResponse })
            });

            if (!imageResponse.ok) throw new Error('Image generation failed');
            const imageData = await imageResponse.json();
            
            if (imageData.status === 'success') {
                updateLoadingStatus('Loading generated image...', 0.8);
                const img = new Image();
                
                img.onload = function() {
                    updateLoadingStatus('CodeBeast generation complete!', 1.0);
                    
                    // Create canvas with overlaid text
                    const canvas = overlayText(img, "Generated for " + message);
                    canvas.className = 'generated-image';
                    
                    // Create info and button group container
                    const infoAndButtons = document.createElement('div');
                    infoAndButtons.className = 'info-and-buttons';

                    // Add GitHub info to the left side
                    const leftSideInfo = document.createElement('div');
                    leftSideInfo.className = 'left-side-info';
                    const githubInfo = displayGitHubInfo(chatData.github_url, chatData.num_repositories);
                    leftSideInfo.appendChild(githubInfo);

                    // Create button group (separate from left side)
                    const buttonGroup = createButtonGroup(canvas, message);

                    // Add languages list
                    const languagesList = displayLanguages(chatData.languages || []);

                    // Add everything to the container in the correct order
                    infoAndButtons.appendChild(leftSideInfo);
                    infoAndButtons.appendChild(buttonGroup);  // Buttons in the middle
                    infoAndButtons.appendChild(languagesList);

                    // Clear and update image container
                    imageContainer.innerHTML = '';
                    imageContainer.appendChild(canvas);

                    // Add to content section
                    document.querySelector('.content-section').appendChild(infoAndButtons);
                    
                    // Only remove the progress bar, keep the status text
                    setTimeout(() => {
                        NProgress.done();
                    }, 500);
                };
                
                img.onerror = function() {
                    throw new Error('Failed to load image');
                };

                img.src = `${imageData.image_url}?t=${Date.now()}`;
            }
        }
    } catch (error) {
        console.error('Error:', error);
        NProgress.done();
        statusText.classList.remove('active');
    }
}

/**
 * Adds text overlay to the generated image
 * @param {HTMLImageElement} image - Source image
 * @param {string} text - Text to overlay
 * @returns {HTMLCanvasElement} Canvas with image and text
 */
function overlayText(image, text) {
    // Create canvas
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    // Set canvas size to match image
    canvas.width = image.width;
    canvas.height = image.height;
    
    // Draw original image
    ctx.drawImage(image, 0, 0);
    
    // Configure text style
    ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.8)';
    ctx.lineWidth = 4;
    
    // Calculate font size based on image size
    const fontSize = Math.max(20, Math.min(40, image.width * 0.05));
    ctx.font = `${fontSize}px Inter`;
    
    // Position text in bottom right corner with padding
    const padding = fontSize;
    const textMetrics = ctx.measureText(text);
    const x = canvas.width - textMetrics.width - padding;
    const y = canvas.height - padding;
    
    // Draw text with stroke for better visibility
    ctx.strokeText(text, x, y);
    ctx.fillText(text, x, y);
    
    return canvas;
}

/**
 * Creates the download and share button group
 * @param {HTMLCanvasElement} canvas - Canvas element containing the image
 * @param {string} message - GitHub handle used to generate the image
 * @returns {HTMLDivElement} Button group container
 */
function createButtonGroup(canvas, message) {
    const buttonGroup = document.createElement('div');
    buttonGroup.className = 'button-group';
    
    // Download button
    const downloadBtn = document.createElement('button');
    downloadBtn.className = 'action-button';
    downloadBtn.innerHTML = 'Download';
    downloadBtn.onclick = function() {
        const link = document.createElement('a');
        link.download = 'codebeast.png';
        link.href = canvas.toDataURL('image/png');
        link.click();
    };
    
    // Share button
    const shareBtn = document.createElement('button');
    shareBtn.className = 'action-button';
    shareBtn.innerHTML = 'Share on X';
    shareBtn.onclick = function() {
        const text = `Check out my CodeBeast generated for ${message} using GitHub data and Langflow!`;
        const imageUrl = window.location.origin + '/static/temp/generated.png';
        const shareUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(imageUrl)}`;
        window.open(shareUrl, '_blank');
    };
    
    buttonGroup.appendChild(downloadBtn);
    buttonGroup.appendChild(shareBtn);
    return buttonGroup;
}

function displayLanguages(languages = []) {
    const languagesList = document.createElement('div');
    languagesList.className = 'languages-list';
    
    if (languages.length > 0) {
        // Create rows of 3 languages
        for (let i = 0; i < languages.length; i += 3) {
            const row = document.createElement('div');
            row.className = 'language-row';
            
            // Get next 3 languages (or remaining languages if less than 3)
            const rowLanguages = languages.slice(i, i + 3);
            
            rowLanguages.forEach(lang => {
                const span = document.createElement('span');
                span.textContent = lang;
                span.className = 'language-tag';
                row.appendChild(span);
            });
            
            languagesList.appendChild(row);
        }
    } else {
        const span = document.createElement('span');
        span.textContent = 'No languages found';
        span.className = 'language-tag placeholder';
        languagesList.appendChild(span);
    }
    
    return languagesList;
}

function displayGitHubInfo(githubUrl, numRepos) {
    const githubInfo = document.createElement('div');
    githubInfo.className = 'github-info';
    
    const username = githubUrl.split('/').pop();
    const link = document.createElement('span');
    link.className = 'github-tag';
    link.innerHTML = `<a href="${githubUrl}" target="_blank">@${username}</a>`;
    githubInfo.appendChild(link);
    
    const repoCount = document.createElement('span');
    repoCount.className = 'github-tag';
    repoCount.textContent = `${numRepos} repos`;
    githubInfo.appendChild(repoCount);
    
    return githubInfo;
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('user-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});