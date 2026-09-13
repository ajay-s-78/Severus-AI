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

  // CSV Attachment Handling
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

      if (!file.name.endsWith('.csv')) {
        alert('Only CSV files (.csv) are supported.');
        return;
      }

      csvFileName.textContent = file.name;
      csvAttachmentBadge.classList.remove('hidden');

      // Upload CSV to backend for safe profiling analysis
      const formData = new FormData();
      formData.append('file', file);
      if (currentSessionId) {
        formData.append('session_id', currentSessionId);
      }

      try {
        const res = await fetch('/api/upload-csv', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        if (res.ok && data.status === 'success') {
          if (!currentSessionId) {
            currentSessionId = data.session_id;
            const title = `CSV: ${file.name}`;
            recentChats.unshift({ id: currentSessionId, title: title, timestamp: Date.now() });
            saveRecentChats();
            renderRecentChatsList();
            barChatTitle.textContent = title;
          }
          showConversationView();
          appendAIMessage(data.analysis.summary_markdown);
          if (!userInput.value.trim()) {
            userInput.value = 'Analyze this dataset and suggest EDA visualization steps.';
            userInput.dispatchEvent(new Event('input'));
          }
        } else {
          alert(data.detail || 'Failed to analyze uploaded CSV dataset.');
        }
      } catch (err) {
        alert('Network error while uploading CSV dataset.');
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
      if (btnElement) {
        btnElement.classList.add('speaking');
        btnElement.innerHTML = '<i class="fa-solid fa-square"></i> Stop';
        btnElement.title = 'Stop Speaking';
        currentSpeakingBtn = btnElement;
      }
    };

    utterance.onend = () => {
      if (btnElement) {
        resetSpeakingBtnState(btnElement);
      }
      if (currentSpeakingBtn === btnElement) {
        currentSpeakingBtn = null;
      }
    };

    utterance.onerror = (e) => {
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
    if (!text) return;

    // If no active session, create a new session ID and recent chat title
    let isFirstMessage = false;
    if (!currentSessionId) {
      currentSessionId = 'session_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
      isFirstMessage = true;
      const title = generateChatTitle(text);
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
    appendUserMessage(text);

    // Reset Input Box
    userInput.value = '';
    userInput.style.height = 'auto';
    sendBtn.disabled = true;

    // Show Typing loading indicator
    showTyping(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          session_id: currentSessionId
        })
      });

      const data = await res.json();

      showTyping(false);
      sendBtn.disabled = false;

      if (res.ok && data.response) {
        appendAIMessage(data.response, data.action_required);
      } else {
        const errorMsg = data.detail || 'An unexpected error occurred while communicating with Severus.';
        appendAIMessage(`⚠️ **Error**: ${errorMsg}`);
      }
    } catch (err) {
      showTyping(false);
      sendBtn.disabled = false;
      appendAIMessage(`⚠️ **Network Error**: Unable to reach Severus backend server. Please check your local connection or server status.`);
    }
  }

  function appendUserMessage(text) {
    const row = document.createElement('div');
    row.className = 'msg-row user-msg-row';

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar user-avatar';
    avatar.innerHTML = '<i class="fa-solid fa-user"></i>';

    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble user-bubble';
    bubble.textContent = text;

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
});
