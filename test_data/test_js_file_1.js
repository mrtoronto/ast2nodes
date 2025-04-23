// DOM Elements
let htmlEditor;
let preview;
let chatInput;
let sendMessage;
let chatMessages;
let runButton;
let previewToggle;
let fullPreview;
let fullPreviewFrame;
let apiKeyInput;
let apiKeyStatus;

// Initialize the editor
function initializeEditor() {
    // Get DOM elements
    htmlEditor = document.getElementById('htmlEditor');
    preview = document.getElementById('preview');
    chatInput = document.getElementById('chatInput');
    sendMessage = document.getElementById('sendMessage');
    chatMessages = document.getElementById('chatMessages');
    runButton = document.getElementById('runButton');
    previewToggle = document.getElementById('previewToggle');
    fullPreview = document.getElementById('fullPreview');
    fullPreviewFrame = document.getElementById('fullPreviewFrame');
    apiKeyInput = document.getElementById('apiKeyInput');
    apiKeyStatus = document.getElementById('apiKeyStatus');
    
    // Load saved content or use default
    const savedContent = localStorage.getItem(STORAGE_KEYS.HTML_CONTENT);
    htmlEditor.value = savedContent || DEFAULT_HTML;
    
    // Load saved API key
    const savedApiKey = localStorage.getItem(STORAGE_KEYS.API_KEY);
    if (savedApiKey) {
        apiKeyInput.value = savedApiKey;
        apiKeyStatus.classList.add('valid');
    }
    
    // Load conversation history
    const savedHistory = localStorage.getItem(STORAGE_KEYS.CONVERSATION_HISTORY);
    if (savedHistory) {
        const history = JSON.parse(savedHistory);
        history.forEach(msg => {
            addMessage(msg.content, msg.role === 'user');
        });
    }
    
    // Update preview
    updatePreview();
    
    // Add event listeners
    htmlEditor.addEventListener('input', () => {
        saveContent();
    });

    previewToggle.addEventListener('change', () => {
        if (previewToggle.checked) {
            fullPreview.style.display = 'block';
            fullPreviewFrame.srcdoc = htmlEditor.value;
        } else {
            fullPreview.style.display = 'none';
        }
    });

    // Add chat input listener
    sendMessage.addEventListener('click', () => {
        const message = chatInput.value.trim();
        if (message) {
            handleChatMessage(message);
            chatInput.value = '';
        }
    });

    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const message = chatInput.value.trim();
            if (message) {
                handleChatMessage(message);
                chatInput.value = '';
            }
        }
    });
}

// Update the preview with visual feedback
function updatePreview() {
    // Add visual feedback
    preview.classList.add('opacity-50');
    runButton.classList.add('animate-pulse');
    
    // Create an iframe to isolate the preview
    const iframe = document.createElement('iframe');
    iframe.srcdoc = htmlEditor.value;
    iframe.style.width = '100%';
    iframe.style.height = '100%';
    iframe.style.border = 'none';
    
    // Clear and update the preview
    preview.innerHTML = '';
    preview.appendChild(iframe);

    // Update full preview if it's visible
    if (previewToggle.checked) {
        fullPreviewFrame.srcdoc = htmlEditor.value;
    }
    
    // Remove visual feedback after a short delay
    setTimeout(() => {
        preview.classList.remove('opacity-50');
        runButton.classList.remove('animate-pulse');
    }, 300);
}

// Save content to localStorage
function saveContent() {
    localStorage.setItem(STORAGE_KEYS.HTML_CONTENT, htmlEditor.value);
}

// Reset function
function resetEditor() {
    // Reset HTML content
    htmlEditor.value = DEFAULT_HTML;
    updatePreview();
    saveContent();
    
    // Clear chat history
    localStorage.removeItem(STORAGE_KEYS.CONVERSATION_HISTORY);
    chatMessages.innerHTML = '';
    
    // Show confirmation message
    addMessage("Editor has been reset to default state.", false);
} 