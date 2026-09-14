// SEVERUS — Data Science AI Assistant ChatGPT-Style UI Script

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const sidebar = document.getElementById('sidebar');
  const collapseSidebarBtn = document.getElementById('collapseSidebarBtn');
  const expandSidebarBtn = document.getElementById('expandSidebarBtn');
  const newChatBtn = document.getElementById('newChatBtn');
  const headerNewChatBtn = document.getElementById('headerNewChatBtn');
  const clearAllChatsBtn = document.getElementById('clearAllChatsBtn');
  const recentChatsList = document.getElementById('recentChatsList');
  const barChatTitle = document.getElementById('barChatTitle');

  const welcomeScreen = document.getElementById('welcomeScreen');
  const messagesWrapper = document.getElementById('messagesWrapper');
  const messagesContainer = document.getElementById('messagesContainer');
  const typingIndicator = document.getElementById('typingIndicator');

  const userInput = document.getElementById('userInput');
  const sendBtn = document.getElementById('sendBtn');

  // Application State
  let currentSessionId = null;
  let recentChats = JSON.parse(localStorage.getItem('severus_recent_chats') || '[]');
  let currentImageData = null;

  // JARVIS Status Indicator Helper
  const jarvisStatusDot = document.getElementById('jarvisStatusDot');
  const jarvisStatusText = document.getElementById('jarvisStatusText');

  // Voice Status Indicator Elements
  const voiceStatusRow = document.getElementById('voiceStatusRow');
  const voiceStatusText = document.getElementById('voiceStatusText');

  function setVoiceStatus(status) {
    if (!voiceStatusRow || !voiceStatusText) return;
    voiceStatusRow.className = 'status-row voice-status-row';
    if (status === 'AUTHORIZED_OWNER') {
      voiceStatusRow.classList.add('authorized');
      voiceStatusText.textContent = 'Voice: Authorized Owner';
    } else {
      voiceStatusRow.classList.add('chat-only');
      voiceStatusText.textContent = 'Voice: Chat Only Mode';
    }
  }

  function setJarvisStatus(state, customLabel = null) {
    if (!jarvisStatusText || !jarvisStatusDot) return;
    jarvisStatusDot.className = 'status-dot';

    switch (state) {
      case 'thinking':
        jarvisStatusDot.classList.add('thinking');
        jarvisStatusText.textContent = customLabel || 'SEVERUS: Thinking...';
        break;
      case 'searching':
        jarvisStatusDot.classList.add('searching');
        jarvisStatusText.textContent = customLabel || 'SEVERUS: Searching Web...';
        break;
      case 'vision':
        jarvisStatusDot.classList.add('vision');
        jarvisStatusText.textContent = customLabel || 'SEVERUS: Analyzing Image...';
        break;
      case 'awaiting':
        jarvisStatusDot.classList.add('awaiting');
        jarvisStatusText.textContent = customLabel || 'SEVERUS: Awaiting Confirmation...';
        break;
      case 'speaking':
        jarvisStatusDot.classList.add('speaking');
        jarvisStatusText.textContent = customLabel || 'SEVERUS: Speaking...';
        break;
      case 'ready':
      default:
        jarvisStatusText.textContent = customLabel || 'SEVERUS: Ready';
        break;
    }
  }

  // Configure marked markdown options
  if (window.marked) {
    marked.setOptions({
      highlight: function(code, lang) {
        if (lang && hljs.getLanguage(lang)) {
          return hljs.highlight(code, { language: lang }).value;
        }
        return hljs.highlightAuto(code).value;
      },
      breaks: true
    });
  }

  // Initialize UI
  renderRecentChatsList();
  showWelcomeScreen();

  // Sidebar Toggle Event Listeners
  if (collapseSidebarBtn) {
    collapseSidebarBtn.addEventListener('click', () => {
      sidebar.classList.add('collapsed');
    });
  }

  if (expandSidebarBtn) {
    expandSidebarBtn.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
    });
  }

  // New Chat Event Listeners
  newChatBtn.addEventListener('click', startNewChat);
  headerNewChatBtn.addEventListener('click', startNewChat);

  // Clear All Recent Chats Listener
  clearAllChatsBtn.addEventListener('click', () => {
    if (confirm('Are you sure you want to clear all recent chats?')) {
      recentChats.forEach(chat => {
        fetch('/api/clear', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: chat.id })
        }).catch(() => {});
      });
      recentChats = [];
      saveRecentChats();
      renderRecentChatsList();
      startNewChat();
    }
  });

  // Clear Memory Event Listener
  const clearMemoryBtn = document.getElementById('clearMemoryBtn');
  if (clearMemoryBtn) {
    clearMemoryBtn.addEventListener('click', async () => {
      if (confirm('Are you sure you want to clear all stored Severus conversation memory across sessions?')) {
        try {
          const res = await fetch('/api/memory', { method: 'DELETE' });
          const data = await res.json();
          if (res.ok && data.status === 'cleared') {
            alert(`Successfully cleared ${data.deleted_count} stored memory items.`);
          } else {
            alert('Failed to clear conversation memory.');
          }
        } catch (err) {
          alert('Error connecting to server to clear memory.');
        }
      }
    });
  }

  // Prompt Cards Click Handling on Welcome Screen
  const promptGrid = document.querySelector('.prompt-grid');
  if (promptGrid) {
    promptGrid.addEventListener('click', (e) => {
      const card = e.target.closest('.prompt-card');
      if (card) {
        const prompt = card.getAttribute('data-prompt');
        if (prompt) {
          userInput.value = prompt;
          userInput.dispatchEvent(new Event('input'));
          sendMessage();
        }
      }
    });
  }

  // Textarea Auto-Expansion & Keyboard Navigation
  userInput.addEventListener('input', () => {
    userInput.style.height = 'auto';
    userInput.style.height = Math.min(userInput.scrollHeight, 160) + 'px';
  });

  userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Image Attachment Handling (Phase 6: Vision)
  const attachImageBtn = document.getElementById('attachImageBtn');
  const imageFileInput = document.getElementById('imageFileInput');
  const imageAttachmentBadge = document.getElementById('imageAttachmentBadge');
  const imageFileName = document.getElementById('imageFileName');
  const removeImageBtn = document.getElementById('removeImageBtn');

  if (attachImageBtn && imageFileInput) {
    attachImageBtn.addEventListener('click', () => {
      imageFileInput.click();
    });

    imageFileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (!file) return;

      const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
      if (!allowedTypes.includes(file.type.toLowerCase())) {
        alert('Unsupported image format. Allowed formats: PNG, JPG, JPEG, WEBP.');
        imageFileInput.value = '';
        return;
      }

      if (file.size > 10 * 1024 * 1024) {
        alert('Image file size exceeds the 10 MB limit.');
        imageFileInput.value = '';
        return;
      }

      const reader = new FileReader();
      reader.onload = (event) => {
        currentImageData = event.target.result;
        imageFileName.textContent = file.name;
        imageAttachmentBadge.classList.remove('hidden');
      };
      reader.readAsDataURL(file);
    });

    if (removeImageBtn) {
      removeImageBtn.addEventListener('click', () => {
        clearImageAttachment();
      });
    }
  }

  function clearImageAttachment() {
    currentImageData = null;
    if (imageFileInput) imageFileInput.value = '';
    if (imageAttachmentBadge) imageAttachmentBadge.classList.add('hidden');
  }

  // Dataset Attachment Handling (Phase 8: Data Science Workspace)
  const attachCsvBtn = document.getElementById('attachCsvBtn');
  const csvFileInput = document.getElementById('csvFileInput');
  const csvAttachmentBadge = document.getElementById('csvAttachmentBadge');
  const csvFileName = document.getElementById('csvFileName');
  const removeCsvBtn = document.getElementById('removeCsvBtn');

  if (attachCsvBtn && csvFileInput) {
    attachCsvBtn.addEventListener('click', () => {
      csvFileInput.click();
    });

    csvFileInput.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      const ext = "." + file.name.split('.').pop().toLowerCase();
      const allowedExts = ['.csv', '.xlsx', '.xls', '.json', '.txt'];
      if (!allowedExts.includes(ext)) {
        alert('Unsupported file format. Supported dataset formats: CSV, Excel (.xlsx), JSON, TXT.');
        csvFileInput.value = '';
        return;
      }

      if (file.size > 15 * 1024 * 1024) {
        alert('Dataset file size exceeds the 15 MB limit.');
        csvFileInput.value = '';
        return;
      }

      csvFileName.textContent = file.name;
      csvAttachmentBadge.classList.remove('hidden');

      setJarvisStatus('thinking', 'JARVIS: Loading Dataset...');

      // Upload Dataset to backend for safe profiling analysis
      const formData = new FormData();
      formData.append('file', file);
      if (currentSessionId) {
        formData.append('session_id', currentSessionId);
      }

      try {
        setJarvisStatus('thinking', 'JARVIS: Analyzing Data...');
        const res = await fetch('/api/upload-dataset', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        if (res.ok && data.status === 'success') {
          setJarvisStatus('thinking', 'JARVIS: Generating Insights...');
          if (!currentSessionId) {
            currentSessionId = data.session_id;
            const title = `Dataset: ${file.name}`;
            recentChats.unshift({ id: currentSessionId, title: title, timestamp: Date.now() });
            saveRecentChats();
            renderRecentChatsList();
            barChatTitle.textContent = title;
          }
          showConversationView();
          appendAIMessage(data.analysis.summary_markdown);
          setJarvisStatus('ready');
          if (!userInput.value.trim()) {
            userInput.value = 'Explain this dataset, missing values, summary statistics, and important patterns.';
            userInput.dispatchEvent(new Event('input'));
          }
        } else {
          setJarvisStatus('ready');
          alert(data.detail || 'Failed to analyze uploaded dataset.');
        }
      } catch (err) {
        setJarvisStatus('ready');
        alert('Network error while uploading dataset.');
      }
    });

    if (removeCsvBtn) {
      removeCsvBtn.addEventListener('click', () => {
        csvFileInput.value = '';
        csvAttachmentBadge.classList.add('hidden');
      });
    }
  }

  // Web Speech API Voice Input Handling (Speech-to-Text)
  const micBtn = document.getElementById('micBtn');
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (micBtn) {
    if (!SpeechRecognition) {
      micBtn.title = 'Speech recognition is not supported in this browser';
      micBtn.addEventListener('click', () => {
        alert('Speech recognition is not supported in this browser. Please use Google Chrome, Microsoft Edge, or Safari.');
      });
    } else {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      let isListening = false;
      let existingText = '';

      micBtn.addEventListener('click', () => {
        if (isListening) {
          recognition.stop();
        } else {
          existingText = userInput.value;
          try {
            recognition.start();
          } catch (e) {
            console.error('Speech recognition start error:', e);
          }
        }
      });

      recognition.onstart = () => {
        isListening = true;
        micBtn.classList.add('listening');
        micBtn.title = 'Listening... Click to stop voice input';
      };

      recognition.onresult = (event) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          transcript += event.results[i][0].transcript;
        }

        const prefix = existingText ? (existingText.trim() + ' ') : '';
        userInput.value = prefix + transcript;
        userInput.dispatchEvent(new Event('input'));
      };

      recognition.onerror = (event) => {
        console.warn('Speech recognition error:', event.error);
        if (event.error === 'not-allowed') {
          alert('Microphone permission was denied. Please allow microphone access in your browser settings.');
        }
        stopListeningState();
      };

      recognition.onend = () => {
        stopListeningState();
      };

      function stopListeningState() {
        isListening = false;
        micBtn.classList.remove('listening');
        micBtn.title = 'Voice Input (Speech to Text)';
      }
    }
  }

  // =========================================================================
  // WEB SPEECH SYNTHESIS API (PHASE 2: TEXT-TO-SPEECH VOICE OUTPUT)
  // =========================================================================
  const speechSynthesisSupported = 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;
  const autoVoiceToggleBtn = document.getElementById('autoVoiceToggleBtn');
  let autoVoiceEnabled = JSON.parse(localStorage.getItem('severus_auto_voice') || 'false');
  let currentSpeakingBtn = null;

  function updateAutoVoiceToggleUI() {
    if (!autoVoiceToggleBtn) return;
    if (!speechSynthesisSupported) {
      autoVoiceToggleBtn.title = 'Text-to-Speech is not supported in this browser';
      autoVoiceToggleBtn.disabled = true;
      return;
    }
    if (autoVoiceEnabled) {
      autoVoiceToggleBtn.classList.add('active');
      autoVoiceToggleBtn.innerHTML = '<i class="fa-solid fa-volume-high"></i> <span class="btn-text">Auto Voice: On</span>';
    } else {
      autoVoiceToggleBtn.classList.remove('active');
      autoVoiceToggleBtn.innerHTML = '<i class="fa-solid fa-volume-xmark"></i> <span class="btn-text">Auto Voice: Off</span>';
    }
  }

  if (autoVoiceToggleBtn) {
    updateAutoVoiceToggleUI();
    autoVoiceToggleBtn.addEventListener('click', () => {
      if (!speechSynthesisSupported) return;
      autoVoiceEnabled = !autoVoiceEnabled;
      localStorage.setItem('severus_auto_voice', JSON.stringify(autoVoiceEnabled));
      updateAutoVoiceToggleUI();
    });
  }

  function resetSpeakingBtnState(btn) {
    if (!btn) return;
    btn.classList.remove('speaking');
    btn.innerHTML = '<i class="fa-solid fa-volume-high"></i> Read Aloud';
    btn.title = 'Read Aloud';
  }

  function stopAllSpeech() {
    if (speechSynthesisSupported && window.speechSynthesis.speaking) {
      window.speechSynthesis.cancel();
    }
    if (currentSpeakingBtn) {
      resetSpeakingBtnState(currentSpeakingBtn);
      currentSpeakingBtn = null;
    }
  }

  function speakMessageText(text, btnElement) {
    if (!speechSynthesisSupported) {
      alert('Speech synthesis is not supported in this browser.');
      return;
    }

    const synth = window.speechSynthesis;

    if (btnElement && currentSpeakingBtn === btnElement && (synth.speaking || synth.pending)) {
      stopAllSpeech();
      return;
    }

    stopAllSpeech();

    if (!text || !text.trim()) return;

    const cleanText = text
      .replace(/```[\s\S]*?```/g, ' Code snippet omitted. ')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/[*#_~]/g, '')
      .trim();

    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.lang = 'en-US';

    utterance.onstart = () => {
      setJarvisStatus('speaking');
      if (btnElement) {
        btnElement.classList.add('speaking');
        btnElement.innerHTML = '<i class="fa-solid fa-square"></i> Stop';
        btnElement.title = 'Stop Speaking';
        currentSpeakingBtn = btnElement;
      }
    };

    utterance.onend = () => {
      setJarvisStatus('ready');
      if (btnElement) {
        resetSpeakingBtnState(btnElement);
      }
      if (currentSpeakingBtn === btnElement) {
        currentSpeakingBtn = null;
      }
    };

    utterance.onerror = (e) => {
      setJarvisStatus('ready');
      console.warn('Speech synthesis error:', e);
      if (btnElement) {
        resetSpeakingBtnState(btnElement);
      }
      if (currentSpeakingBtn === btnElement) {
        currentSpeakingBtn = null;
      }
    };

    synth.speak(utterance);
  }


  sendBtn.addEventListener('click', sendMessage);


  // =========================================================================
  // CORE FUNCTIONS
  // =========================================================================

  function startNewChat() {
    stopAllSpeech();
    currentSessionId = null;
    clearImageAttachment();
    setJarvisStatus('ready');
    barChatTitle.textContent = 'SEVERUS';
    showWelcomeScreen();
    userInput.value = '';
    userInput.style.height = 'auto';
    renderRecentChatsList();
  }


  function showWelcomeScreen() {
    welcomeScreen.classList.remove('hidden');
    messagesWrapper.classList.add('hidden');
    messagesContainer.innerHTML = '';
  }

  function showConversationView() {
    welcomeScreen.classList.add('hidden');
    messagesWrapper.classList.remove('hidden');
  }

  async function sendMessage() {
    const text = userInput.value.trim();
    const sendingImageData = currentImageData;

    if (!text && !sendingImageData) return;
    const promptText = text || 'Analyze this image in detail.';

    // If no active session, create a new session ID and recent chat title
    let isFirstMessage = false;
    if (!currentSessionId) {
      currentSessionId = 'session_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
      isFirstMessage = true;
      const title = generateChatTitle(promptText);
      recentChats.unshift({
        id: currentSessionId,
        title: title,
        timestamp: Date.now()
      });
      saveRecentChats();
      renderRecentChatsList();
      barChatTitle.textContent = title;
    }

    // Show conversation stream & append User message
    showConversationView();
    appendUserMessage(promptText, sendingImageData);

    // Reset Input Box & Attachment
    userInput.value = '';
    userInput.style.height = 'auto';
    clearImageAttachment();
    sendBtn.disabled = true;

    // Set JARVIS UI status
    if (sendingImageData) {
      setJarvisStatus('vision');
    } else if (/\b(latest|recent|current|news|today|2025|2026|weather)\b/i.test(promptText)) {
      setJarvisStatus('searching');
    } else {
      setJarvisStatus('thinking');
    }

    // Show Typing loading indicator
    showTyping(true);

    try {
      const payload = {
        message: promptText,
        session_id: currentSessionId
      };
      if (sendingImageData) {
        payload.image_data = sendingImageData;
      }

      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();

      showTyping(false);
      sendBtn.disabled = false;

      if (data.speaker_status) {
        setVoiceStatus(data.speaker_status);
      }

      if (data.action_required) {
        setJarvisStatus('awaiting');
      } else {
        setJarvisStatus('ready');
      }

      if (res.ok && data.response) {
        appendAIMessage(data.response, data.action_required);
      } else {
        const errorMsg = data.detail || 'An unexpected error occurred while communicating with Severus.';
        appendAIMessage(`⚠️ **Error**: ${errorMsg}`);
      }
    } catch (err) {
      showTyping(false);
      sendBtn.disabled = false;
      setJarvisStatus('ready');
      appendAIMessage(`⚠️ **Network Error**: Unable to reach Severus backend server. Please check your local connection or server status.`);
    }
  }

  function appendUserMessage(text, imageData = null) {
    const row = document.createElement('div');
    row.className = 'msg-row user-msg-row';

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar user-avatar';
    avatar.innerHTML = '<i class="fa-solid fa-user"></i>';

    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble user-bubble';

    if (imageData) {
      const img = document.createElement('img');
      img.src = imageData;
      img.className = 'user-msg-image-thumb';
      img.style.maxWidth = '240px';
      img.style.maxHeight = '240px';
      img.style.borderRadius = '8px';
      img.style.marginBottom = '8px';
      img.style.display = 'block';
      bubble.appendChild(img);
    }

    const textSpan = document.createElement('div');
    textSpan.textContent = text;
    bubble.appendChild(textSpan);

    row.appendChild(avatar);
    row.appendChild(bubble);

    messagesContainer.appendChild(row);
    scrollToBottom();
  }

  function appendAIMessage(rawMarkdown, actionRequired = null) {
    const row = document.createElement('div');
    row.className = 'msg-row ai-msg-row';

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar ai-avatar';
    avatar.innerHTML = '<i class="fa-solid fa-brain"></i>';

    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble ai-bubble';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'msg-content';

    if (window.marked) {
      contentDiv.innerHTML = marked.parse(rawMarkdown);
    } else {
      contentDiv.textContent = rawMarkdown;
    }

    // Format Code blocks with language badges & Copy Code button
    enhanceCodeBlocks(contentDiv);

    bubble.appendChild(contentDiv);

    // If computer control action confirmation is required, append Confirmation Card UI
    if (actionRequired) {
      const card = document.createElement('div');
      card.className = 'action-card';
      card.innerHTML = `
        <div class="action-card-header">
          <i class="fa-solid fa-shield-halved"></i>
          <span>Desktop Action Safety Confirmation</span>
        </div>
        <div class="action-card-body">
          <p><strong>Action:</strong> <code>${escapeHtml(actionRequired.action_type)}</code></p>
          <p><strong>Target:</strong> <code>${escapeHtml(actionRequired.target)}</code></p>
        </div>
        <div class="action-card-actions">
          <button class="btn-confirm-action"><i class="fa-solid fa-check"></i> Confirm & Execute</button>
          <button class="btn-cancel-action"><i class="fa-solid fa-xmark"></i> Cancel</button>
        </div>
        <div class="action-card-status hidden"></div>
      `;

      const confirmBtn = card.querySelector('.btn-confirm-action');
      const cancelBtn = card.querySelector('.btn-cancel-action');
      const statusDiv = card.querySelector('.action-card-status');

      confirmBtn.addEventListener('click', async () => {
        confirmBtn.disabled = true;
        cancelBtn.disabled = true;
        confirmBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Executing...';

        try {
          const actRes = await fetch('/api/execute-action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              action_type: actionRequired.action_type,
              target: actionRequired.target,
              confirmed: true,
              session_id: currentSessionId
            })
          });
          const actData = await actRes.json();
          statusDiv.classList.remove('hidden');
          if (actRes.ok && actData.status === 'success') {
            statusDiv.className = 'action-card-status success';
            statusDiv.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${escapeHtml(actData.message)}`;
            confirmBtn.innerHTML = '<i class="fa-solid fa-check"></i> Executed';
          } else {
            statusDiv.className = 'action-card-status error';
            statusDiv.innerHTML = `<i class="fa-solid fa-circle-xmark"></i> ${escapeHtml(actData.message || 'Execution failed.')}`;
            confirmBtn.innerHTML = '<i class="fa-solid fa-xmark"></i> Failed';
          }
        } catch (e) {
          statusDiv.classList.remove('hidden');
          statusDiv.className = 'action-card-status error';
          statusDiv.innerHTML = '<i class="fa-solid fa-circle-xmark"></i> Network error during execution.';
        }
      });

      cancelBtn.addEventListener('click', () => {
        confirmBtn.disabled = true;
        cancelBtn.disabled = true;
        statusDiv.classList.remove('hidden');
        statusDiv.className = 'action-card-status info';
        statusDiv.innerHTML = '<i class="fa-solid fa-ban"></i> Action cancelled by user.';
      });

      bubble.appendChild(card);
    }

    // Read Aloud Speaker Control Footer (Phase 2)
    if (speechSynthesisSupported) {
      const footer = document.createElement('div');
      footer.className = 'msg-footer';

      const speakBtn = document.createElement('button');
      speakBtn.className = 'btn-speak-msg';
      speakBtn.title = 'Read Aloud';
      speakBtn.innerHTML = '<i class="fa-solid fa-volume-high"></i> Read Aloud';

      speakBtn.addEventListener('click', () => {
        speakMessageText(contentDiv.innerText, speakBtn);
      });

      footer.appendChild(speakBtn);
      bubble.appendChild(footer);

      if (autoVoiceEnabled) {
        setTimeout(() => {
          speakMessageText(contentDiv.innerText, speakBtn);
        }, 150);
      }
    }

    row.appendChild(avatar);
    row.appendChild(bubble);


    messagesContainer.appendChild(row);
    scrollToBottom();
  }

  function enhanceCodeBlocks(container) {
    const preElements = container.querySelectorAll('pre');
    preElements.forEach((pre) => {
      const code = pre.querySelector('code');
      const langMatch = code ? code.className.match(/language-(\w+)/) : null;
      const lang = langMatch ? langMatch[1] : 'CODE';

      const wrapper = document.createElement('div');
      wrapper.className = 'code-block-wrapper';

      const header = document.createElement('div');
      header.className = 'code-header';
      header.innerHTML = `
        <span><i class="fa-solid fa-code"></i> ${lang.toUpperCase()}</span>
        <button class="copy-btn"><i class="fa-regular fa-copy"></i> Copy</button>
      `;

      const copyBtn = header.querySelector('.copy-btn');
      copyBtn.addEventListener('click', () => {
        const codeText = code ? code.innerText : pre.innerText;
        navigator.clipboard.writeText(codeText).then(() => {
          copyBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
          setTimeout(() => {
            copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i> Copy';
          }, 2000);
        });
      });

      pre.parentNode.insertBefore(wrapper, pre);
      wrapper.appendChild(header);
      wrapper.appendChild(pre);

      if (window.hljs && code) {
        hljs.highlightElement(code);
      }
    });
  }

  async function loadChatSession(sessionId, title) {
    currentSessionId = sessionId;
    barChatTitle.textContent = title;
    showConversationView();
    messagesContainer.innerHTML = '';
    showTyping(true);

    try {
      const res = await fetch(`/api/history/${sessionId}`);
      const data = await res.json();
      showTyping(false);

      if (res.ok && data.messages && data.messages.length > 0) {
        data.messages.forEach(msg => {
          if (msg.role === 'user') {
            appendUserMessage(msg.content);
          } else if (msg.role === 'assistant') {
            appendAIMessage(msg.content);
          }
        });
      } else {
        appendAIMessage(`*Selected recent chat session (${title}) has no prior active messages stored on server.*`);
      }
    } catch (err) {
  showTyping(false);
  console.error('History loading error:', err);
  appendAIMessage(`⚠️ **Error loading conversation history:** ${err.message}`);
}

    renderRecentChatsList();
  }

  function deleteChatSession(sessionId, e) {
    e.stopPropagation();
    fetch('/api/clear', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId })
    }).catch(() => {});

    recentChats = recentChats.filter(chat => chat.id !== sessionId);
    saveRecentChats();
    renderRecentChatsList();

    if (currentSessionId === sessionId) {
      startNewChat();
    }
  }

  function renderRecentChatsList() {
    recentChatsList.innerHTML = '';
    if (recentChats.length === 0) {
      recentChatsList.innerHTML = '<div style="font-size: 0.78rem; color: var(--text-muted); padding: 8px 12px; text-align: center;">No recent chats yet</div>';
      return;
    }

    recentChats.forEach(chat => {
      const item = document.createElement('div');
      item.className = 'recent-chat-item' + (chat.id === currentSessionId ? ' active' : '');

      item.innerHTML = `
        <div class="chat-item-title">
          <i class="fa-regular fa-message"></i>
          <span>${escapeHtml(chat.title)}</span>
        </div>
        <button class="btn-delete-chat" title="Delete Chat">
          <i class="fa-solid fa-xmark"></i>
        </button>
      `;

      item.addEventListener('click', () => loadChatSession(chat.id, chat.title));
      const deleteBtn = item.querySelector('.btn-delete-chat');
      deleteBtn.addEventListener('click', (e) => deleteChatSession(chat.id, e));

      recentChatsList.appendChild(item);
    });
  }

  function generateChatTitle(prompt) {
    if (!prompt) return 'New Conversation';
    const cleaned = prompt.replace(/[\r\n]+/g, ' ').trim();
    if (cleaned.length <= 26) return cleaned;
    return cleaned.substring(0, 26) + '...';
  }

  function saveRecentChats() {
    localStorage.setItem('severus_recent_chats', JSON.stringify(recentChats));
  }

  function showTyping(show) {
    if (show) {
      typingIndicator.classList.remove('hidden');
    } else {
      typingIndicator.classList.add('hidden');
    }
    scrollToBottom();
  }

  function scrollToBottom() {
    const chatViewport = document.querySelector('.chat-viewport');
    if (chatViewport) {
      chatViewport.scrollTop = chatViewport.scrollHeight;
    }
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // ==========================================================================
  // ML WORKSPACE MODAL EVENT HANDLERS
  // ==========================================================================
  const mlWorkspaceBtn = document.getElementById('mlWorkspaceBtn');
  const mlModalOverlay = document.getElementById('mlModalOverlay');
  const closeMlModalBtn = document.getElementById('closeMlModalBtn');
  const mlRecommendBtn = document.getElementById('mlRecommendBtn');
  const mlTrainSubmitBtn = document.getElementById('mlTrainSubmitBtn');
  const mlFileInput = document.getElementById('mlFileInput');
  const mlTargetInput = document.getElementById('mlTargetInput');
  const mlProblemTypeSelect = document.getElementById('mlProblemTypeSelect');
  const mlAlgorithmSelect = document.getElementById('mlAlgorithmSelect');
  const mlRecommendationBox = document.getElementById('mlRecommendationBox');

  if (mlWorkspaceBtn && mlModalOverlay) {
    mlWorkspaceBtn.addEventListener('click', () => {
      mlModalOverlay.classList.remove('hidden');
    });

    if (closeMlModalBtn) {
      closeMlModalBtn.addEventListener('click', () => {
        mlModalOverlay.classList.add('hidden');
      });
    }

    mlModalOverlay.addEventListener('click', (e) => {
      if (e.target === mlModalOverlay) {
        mlModalOverlay.classList.add('hidden');
      }
    });
  }

  if (mlRecommendBtn) {
    mlRecommendBtn.addEventListener('click', async () => {
      const fileToUpload = (mlFileInput && mlFileInput.files[0]) || currentCsvFile;
      if (!fileToUpload) {
        alert('Please select or attach a dataset file (CSV, Excel, JSON, TXT) first.');
        return;
      }

      const formData = new FormData();
      formData.append('file', fileToUpload);
      const targetVal = mlTargetInput ? mlTargetInput.value.trim() : '';
      if (targetVal) formData.append('target_col', targetVal);

      try {
        mlRecommendBtn.disabled = true;
        mlRecommendBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analyzing...';
        
        const res = await fetch('/api/ml-recommendation', {
          method: 'POST',
          body: formData
        });

        const data = await res.json();
        mlRecommendBtn.disabled = false;
        mlRecommendBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Auto Recommend';

        if (res.ok && data.status === 'success') {
          if (mlProblemTypeSelect) mlProblemTypeSelect.value = data.problem_type;
          if (mlAlgorithmSelect) mlAlgorithmSelect.value = data.recommended_algorithm;
          if (mlTargetInput && !mlTargetInput.value) mlTargetInput.value = data.target_column;

          if (mlRecommendationBox) {
            mlRecommendationBox.classList.remove('hidden');
            mlRecommendationBox.innerHTML = `
              <strong><i class="fa-solid fa-robot"></i> Recommendation: ${escapeHtml(data.recommended_algorithm_name)}</strong><br>
              <span style="font-size:0.8rem;">Task: ${data.problem_type} on target '<code>${escapeHtml(data.target_column)}</code>'</span><br>
              <span style="font-size:0.78rem; opacity:0.9;">${escapeHtml(data.rationale)}</span>
            `;
          }
        } else {
          alert(`Recommendation Error: ${data.detail || 'Could not analyze dataset'}`);
        }
      } catch (err) {
        mlRecommendBtn.disabled = false;
        mlRecommendBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Auto Recommend';
        alert(`Error: ${err.message}`);
      }
    });
  }

  if (mlTrainSubmitBtn) {
    mlTrainSubmitBtn.addEventListener('click', async () => {
      const fileToUpload = (mlFileInput && mlFileInput.files[0]) || currentCsvFile;
      const targetCol = mlTargetInput ? mlTargetInput.value.trim() : '';

      if (!fileToUpload) {
        alert('Please select or attach a dataset file (CSV, Excel, JSON, TXT).');
        return;
      }

      if (!targetCol) {
        alert('Please specify a target column name for machine learning training.');
        return;
      }

      if (!currentSessionId) {
        currentSessionId = 'session_' + Date.now();
      }

      const problemType = mlProblemTypeSelect ? mlProblemTypeSelect.value : 'classification';
      const algorithm = mlAlgorithmSelect ? mlAlgorithmSelect.value : 'random_forest';

      mlModalOverlay.classList.add('hidden');
      showConversationView();
      appendUserMessage(`🤖 Train ${algorithm} model on '${fileToUpload.name}' (Target: ${targetCol}, Task: ${problemType})`);

      setJarvisStatus('thinking', 'JARVIS: Training Model...');
      showTyping(true);

      const formData = new FormData();
      formData.append('file', fileToUpload);
      formData.append('target_col', targetCol);
      formData.append('algorithm', algorithm);
      formData.append('problem_type', problemType);
      formData.append('session_id', currentSessionId);

      try {
        const res = await fetch('/api/train-ml-model', {
          method: 'POST',
          body: formData
        });

        const data = await res.json();
        showTyping(false);
        setJarvisStatus('ready', 'JARVIS: Ready');

        if (res.ok && data.status === 'success') {
          appendAIMessage(data.result.summary_markdown);
        } else {
          appendAIMessage(`⚠️ **Machine Learning Training Error:** ${data.detail || 'Training failed.'}`);
        }
      } catch (err) {
        showTyping(false);
        setJarvisStatus('ready', 'SEVERUS: Ready');
        appendAIMessage(`⚠️ **Error executing ML workflow:** ${err.message}`);
      }
    });
  }

  // ==========================================================================
  // ANALYTICS & VISUALIZATION WORKSPACE EVENT HANDLERS
  // ==========================================================================
  const analyticsWorkspaceBtn = document.getElementById('analyticsWorkspaceBtn');
  const analyticsModalOverlay = document.getElementById('analyticsModalOverlay');
  const closeAnalyticsModalBtn = document.getElementById('closeAnalyticsModalBtn');
  const analyticsCloseBtn = document.getElementById('analyticsCloseBtn');
  const analyticsResetBtn = document.getElementById('analyticsResetBtn');

  const analyticsFileInput = document.getElementById('analyticsFileInput');
  const analyticsAnalyzeBtn = document.getElementById('analyticsAnalyzeBtn');
  const analyticsGenerateChartBtn = document.getElementById('analyticsGenerateChartBtn');

  const analyticsStatus = document.getElementById('analyticsStatus');
  const analyticsResults = document.getElementById('analyticsResults');
  const analyticsChartSection = document.getElementById('analyticsChartSection');
  const analyticsChartResult = document.getElementById('analyticsChartResult');
  const analyticsChartImage = document.getElementById('analyticsChartImage');

  const analyticsChartType = document.getElementById('analyticsChartType');
  const analyticsXColumn = document.getElementById('analyticsXColumn');
  const analyticsYColumn = document.getElementById('analyticsYColumn');

  let analyticsCurrentFile = null;
  let analyticsColumns = [];

  // Open Analytics Modal
  if (analyticsWorkspaceBtn && analyticsModalOverlay) {
    analyticsWorkspaceBtn.addEventListener('click', () => {
      analyticsModalOverlay.classList.remove('hidden');
    });
  }

  // Close Analytics Modal
  const closeAnalyticsModal = () => {
    if (analyticsModalOverlay) {
      analyticsModalOverlay.classList.add('hidden');
    }
  };

  if (closeAnalyticsModalBtn) {
    closeAnalyticsModalBtn.addEventListener('click', closeAnalyticsModal);
  }

  if (analyticsCloseBtn) {
    analyticsCloseBtn.addEventListener('click', closeAnalyticsModal);
  }

  if (analyticsModalOverlay) {
    analyticsModalOverlay.addEventListener('click', (e) => {
      if (e.target === analyticsModalOverlay) {
        closeAnalyticsModal();
      }
    });
  }

  // Dataset selection
  if (analyticsFileInput) {
    analyticsFileInput.addEventListener('change', () => {
      const file = analyticsFileInput.files[0];

      if (!file) {
        analyticsCurrentFile = null;
        return;
      }

      analyticsCurrentFile = file;

      if (analyticsStatus) {
        analyticsStatus.classList.remove('hidden');
        analyticsStatus.innerHTML =
          `<i class="fa-solid fa-file-circle-check"></i> Selected: ${escapeHtml(file.name)}`;
      }
    });
  }

  // Analyze Dataset
  if (analyticsAnalyzeBtn) {
    analyticsAnalyzeBtn.addEventListener('click', async () => {
      const fileToAnalyze = analyticsCurrentFile || currentCsvFile;

      if (!fileToAnalyze) {
        alert('Please select a dataset file first.');
        return;
      }

      const formData = new FormData();
      formData.append('file', fileToAnalyze);

      try {
        analyticsAnalyzeBtn.disabled = true;
        analyticsAnalyzeBtn.innerHTML =
          '<i class="fa-solid fa-spinner fa-spin"></i> Analyzing...';

        if (analyticsStatus) {
          analyticsStatus.classList.remove('hidden');
          analyticsStatus.innerHTML =
            '<i class="fa-solid fa-spinner fa-spin"></i> Running advanced analytics...';
        }

        const res = await fetch('/api/analytics/analyze', {
          method: 'POST',
          body: formData
        });

        const data = await res.json();

        if (!res.ok || data.status !== 'success') {
          throw new Error(data.detail || 'Analytics failed.');
        }

        const analysis = data.analysis;

        // Dataset shape
        if (document.getElementById('analyticsRows')) {
          document.getElementById('analyticsRows').textContent =
            analysis.dataset_shape?.rows ?? '-';
        }

        if (document.getElementById('analyticsColumns')) {
          document.getElementById('analyticsColumns').textContent =
            analysis.dataset_shape?.columns ?? '-';
        }

        // Duplicate rows
        if (document.getElementById('analyticsDuplicates')) {
          document.getElementById('analyticsDuplicates').textContent =
            analysis.duplicate_rows ?? '-';
        }

        // Missing values
        if (document.getElementById('analyticsMissing')) {
          const missing = analysis.missing_values || {};
          const totalMissing = Object.values(missing).reduce(
            (sum, item) => {
              if (typeof item === 'number') return sum + item;
              if (typeof item === 'object' && item !== null) {
                return sum + Number(item.count || 0);
              }
              return sum;
            },
            0
          );

          document.getElementById('analyticsMissing').textContent =
            totalMissing;
        }

        // Insights
        const insightsContainer =
          document.getElementById('analyticsInsights');

        if (insightsContainer) {
          const insights = analysis.insights || [];

          if (Array.isArray(insights) && insights.length > 0) {
            insightsContainer.innerHTML = insights
              .map(
                insight =>
                  `<div class="analytics-insight">
                    <i class="fa-solid fa-circle-info"></i>
                    <span>${escapeHtml(String(insight))}</span>
                  </div>`
              )
              .join('');
          } else {
            insightsContainer.innerHTML =
              '<div class="analytics-insight">No additional insights detected.</div>';
          }
        }

        // Extract columns
        analyticsColumns = [
          ...(analysis.numeric_columns || []),
          ...(analysis.categorical_columns || [])
        ];

        populateAnalyticsColumns();

        if (analyticsResults) {
          analyticsResults.classList.remove('hidden');
        }

        if (analyticsChartSection) {
          analyticsChartSection.classList.remove('hidden');
        }

        if (analyticsStatus) {
          analyticsStatus.innerHTML =
            '<i class="fa-solid fa-circle-check"></i> Analysis completed successfully.';
        }

      } catch (err) {
        if (analyticsStatus) {
          analyticsStatus.classList.remove('hidden');
          analyticsStatus.innerHTML =
            `<i class="fa-solid fa-triangle-exclamation"></i> ${escapeHtml(err.message)}`;
        }

        alert(`Analytics Error: ${err.message}`);

      } finally {
        analyticsAnalyzeBtn.disabled = false;
        analyticsAnalyzeBtn.innerHTML =
          '<i class="fa-solid fa-magnifying-glass-chart"></i> Analyze Dataset';
      }
    });
  }

  // Populate X/Y column dropdowns
  function populateAnalyticsColumns() {
    if (!analyticsXColumn || !analyticsYColumn) return;

    analyticsXColumn.innerHTML =
      '<option value="">Auto / Not Required</option>';

    analyticsYColumn.innerHTML =
      '<option value="">Auto / Not Required</option>';

    analyticsColumns.forEach(column => {
      const xOption = document.createElement('option');
      xOption.value = column;
      xOption.textContent = column;
      analyticsXColumn.appendChild(xOption);

      const yOption = document.createElement('option');
      yOption.value = column;
      yOption.textContent = column;
      analyticsYColumn.appendChild(yOption);
    });
  }

  // Generate Chart
  if (analyticsGenerateChartBtn) {
    analyticsGenerateChartBtn.addEventListener('click', async () => {
      const fileToAnalyze = analyticsCurrentFile || currentCsvFile;

      if (!fileToAnalyze) {
        alert('Please select a dataset file first.');
        return;
      }

      const chartType = analyticsChartType
        ? analyticsChartType.value
        : 'histogram';

      const xColumn = analyticsXColumn
        ? analyticsXColumn.value
        : '';

      const yColumn = analyticsYColumn
        ? analyticsYColumn.value
        : '';

      const formData = new FormData();

      formData.append('file', fileToAnalyze);
      formData.append('chart_type', chartType);

      if (xColumn) {
        formData.append('x_column', xColumn);
      }

      if (yColumn) {
        formData.append('y_column', yColumn);
      }

      try {
        analyticsGenerateChartBtn.disabled = true;
        analyticsGenerateChartBtn.innerHTML =
          '<i class="fa-solid fa-spinner fa-spin"></i> Generating...';

        const res = await fetch('/api/analytics/chart', {
          method: 'POST',
          body: formData
        });

        const data = await res.json();

        if (!res.ok || data.status !== 'success') {
          throw new Error(data.detail || 'Chart generation failed.');
        }

        const chart = data.chart;

        if (chart.image_base64 && analyticsChartImage) {
          analyticsChartImage.src =
            `data:image/png;base64,${chart.image_base64}`;

          if (analyticsChartResult) {
            analyticsChartResult.classList.remove('hidden');
          }
        }

      } catch (err) {
        alert(`Chart Error: ${err.message}`);

      } finally {
        analyticsGenerateChartBtn.disabled = false;
        analyticsGenerateChartBtn.innerHTML =
          '<i class="fa-solid fa-chart-line"></i> Generate Chart';
      }
    });
  }

  // Reset Analytics Workspace
  if (analyticsResetBtn) {
    analyticsResetBtn.addEventListener('click', () => {
      analyticsCurrentFile = null;
      analyticsColumns = [];

      if (analyticsFileInput) {
        analyticsFileInput.value = '';
      }

      if (analyticsResults) {
        analyticsResults.classList.add('hidden');
      }

      if (analyticsChartSection) {
        analyticsChartSection.classList.add('hidden');
      }

      if (analyticsChartResult) {
        analyticsChartResult.classList.add('hidden');
      }

      if (analyticsChartImage) {
        analyticsChartImage.src = '';
      }

      if (analyticsStatus) {
        analyticsStatus.classList.add('hidden');
        analyticsStatus.innerHTML = '';
      }

      populateAnalyticsColumns();
    });
  }

  // =========================================================================
  // OWNER VOICE IDENTITY & SPEAKER ENROLLMENT MODAL HANDLERS
  // =========================================================================
  const voiceEnrollBtn = document.getElementById('voiceEnrollBtn');
  const voiceEnrollModalOverlay = document.getElementById('voiceEnrollModalOverlay');
  const closeVoiceEnrollModalBtn = document.getElementById('closeVoiceEnrollModalBtn');
  const closeVoiceModalFooterBtn = document.getElementById('closeVoiceModalFooterBtn');
  const clearVoiceProfileBtn = document.getElementById('clearVoiceProfileBtn');
  const saveVoiceEnrollmentBtn = document.getElementById('saveVoiceEnrollmentBtn');

  const enrollModalStatusIcon = document.getElementById('enrollModalStatusIcon');
  const enrollModalStatusTitle = document.getElementById('enrollModalStatusTitle');
  const enrollModalStatusDesc = document.getElementById('enrollModalStatusDesc');

  const recordVoiceSampleBtn = document.getElementById('recordVoiceSampleBtn');
  const recordSampleStatusText = document.getElementById('recordSampleStatusText');
  const voiceSampleFileInput = document.getElementById('voiceSampleFileInput');

  let recordedAudioSamples = [];

  async function checkSpeakerEnrollmentStatus() {
    try {
      const res = await fetch('/api/speaker/status');
      const data = await res.json();
      if (res.ok && data.enrolled) {
        if (enrollModalStatusIcon) enrollModalStatusIcon.className = 'fa-solid fa-user-check status-icon';
        if (enrollModalStatusTitle) enrollModalStatusTitle.textContent = 'Owner Voice Profile Enrolled';
        if (enrollModalStatusDesc) enrollModalStatusDesc.textContent = `Enrolled with ${data.num_samples} sample(s). Full computer control permitted for verified voice.`;
        if (clearVoiceProfileBtn) clearVoiceProfileBtn.classList.remove('hidden');
        setVoiceStatus('AUTHORIZED_OWNER');
      } else {
        if (enrollModalStatusIcon) enrollModalStatusIcon.className = 'fa-solid fa-user-slash status-icon';
        if (enrollModalStatusTitle) enrollModalStatusTitle.textContent = 'Voice Profile Not Enrolled';
        if (enrollModalStatusDesc) enrollModalStatusDesc.textContent = 'Record or upload owner voice sample to enable full voice computer control.';
        if (clearVoiceProfileBtn) clearVoiceProfileBtn.classList.add('hidden');
        setVoiceStatus('VERIFICATION_UNAVAILABLE');
      }
    } catch (err) {
      console.warn('Failed to check speaker status:', err);
    }
  }

  if (voiceEnrollBtn && voiceEnrollModalOverlay) {
    voiceEnrollBtn.addEventListener('click', () => {
      voiceEnrollModalOverlay.classList.remove('hidden');
      checkSpeakerEnrollmentStatus();
    });

    if (closeVoiceEnrollModalBtn) {
      closeVoiceEnrollModalBtn.addEventListener('click', () => {
        voiceEnrollModalOverlay.classList.add('hidden');
      });
    }

    if (closeVoiceModalFooterBtn) {
      closeVoiceModalFooterBtn.addEventListener('click', () => {
        voiceEnrollModalOverlay.classList.add('hidden');
      });
    }

    if (clearVoiceProfileBtn) {
      clearVoiceProfileBtn.addEventListener('click', async () => {
        if (confirm('Are you sure you want to clear the enrolled owner voice profile?')) {
          try {
            const res = await fetch('/api/speaker/enroll', { method: 'DELETE' });
            if (res.ok) {
              alert('Owner speaker profile cleared.');
              checkSpeakerEnrollmentStatus();
            }
          } catch (err) {
            alert('Failed to clear profile.');
          }
        }
      });
    }

    if (saveVoiceEnrollmentBtn) {
      saveVoiceEnrollmentBtn.addEventListener('click', async () => {
        let samplesToEnroll = [...recordedAudioSamples];

        if (voiceSampleFileInput && voiceSampleFileInput.files.length > 0) {
          const file = voiceSampleFileInput.files[0];
          const reader = new FileReader();
          reader.onload = async (e) => {
            const base64Audio = e.target.result;
            samplesToEnroll.push(base64Audio);
            await submitEnrollment(samplesToEnroll);
          };
          reader.readAsDataURL(file);
          return;
        }

        if (samplesToEnroll.length === 0) {
          // Default synthetic sample enrollment if no manual recording attached
          samplesToEnroll.push("data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=");
        }

        await submitEnrollment(samplesToEnroll);
      });
    }

    async function submitEnrollment(samples) {
      try {
        saveVoiceEnrollmentBtn.disabled = true;
        saveVoiceEnrollmentBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Enrolling...';

        const res = await fetch('/api/speaker/enroll', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ audio_samples: samples })
        });
        const data = await res.json();
        saveVoiceEnrollmentBtn.disabled = false;
        saveVoiceEnrollmentBtn.innerHTML = '<i class="fa-solid fa-check"></i> Enroll Owner Voice';

        if (res.ok && data.status === 'success') {
          alert('Owner voice profile successfully enrolled!');
          checkSpeakerEnrollmentStatus();
          voiceEnrollModalOverlay.classList.add('hidden');
        } else {
          alert(data.detail || data.message || 'Enrollment failed.');
        }
      } catch (err) {
        saveVoiceEnrollmentBtn.disabled = false;
        saveVoiceEnrollmentBtn.innerHTML = '<i class="fa-solid fa-check"></i> Enroll Owner Voice';
        alert('Network error during voice enrollment.');
      }
    }
  }

  // Initial speaker status check on app load
  checkSpeakerEnrollmentStatus();
});
