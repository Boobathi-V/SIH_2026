import React, { useState, useEffect, useRef } from "react";
import { API_BASE_URL } from "../api";
import { getSyncScreeningResult, idbGet } from "../storage";

export default function VoiceAIBuddy({ result: propResult }) {
  const [isOpen, setIsOpen] = useState(false);
  const [result, setResult] = useState(propResult || null);
  const [messages, setMessages] = useState([
    {
      sender: "buddy",
      text: "Hello! I am **Buddy**, your VoiceAI Clinical Assistant. Ask me anything about your diabetic retinopathy screening result, detected lesions, or lifestyle advice!",
      speakText: "Hello! I am Buddy, your Voice AI Clinical Assistant. Ask me anything about your diabetic retinopathy screening result, detected lesions, or lifestyle advice!",
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [inputText, setInputText] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [loading, setLoading] = useState(false);
  const [language, setLanguage] = useState("auto"); // 'auto', 'en', 'ta'
  const [speechSupported, setSpeechSupported] = useState(false);

  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);
  const synthRef = useRef(null);

  // Synchronize result from storage if not passed directly
  useEffect(() => {
    if (propResult) {
      setResult(propResult);
    } else {
      const syncRes = getSyncScreeningResult();
      if (syncRes) setResult(syncRes);
      idbGet("screening_result").then((stored) => {
        if (stored) setResult(stored);
      });
    }
  }, [propResult]);

  // Setup Web Speech API for Voice Input (STT) and Voice Output (TTS)
  useEffect(() => {
    if (typeof window !== "undefined") {
      synthRef.current = window.speechSynthesis;

      const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;

      if (SpeechRecognition) {
        setSpeechSupported(true);
        const recognizer = new SpeechRecognition();
        recognizer.continuous = false;
        recognizer.interimResults = false;
        recognizer.lang = language === "ta" ? "ta-IN" : "en-US";

        recognizer.onstart = () => {
          setIsListening(true);
        };

        recognizer.onresult = (event) => {
          const transcript = event.results[0][0].transcript;
          setIsListening(false);
          if (transcript) {
            handleSendMessage(transcript, true);
          }
        };

        recognizer.onerror = (event) => {
          console.warn("Speech recognition error:", event.error);
          setIsListening(false);
        };

        recognizer.onend = () => {
          setIsListening(false);
        };

        recognitionRef.current = recognizer;
      }
    }

    return () => {
      if (synthRef.current) synthRef.current.cancel();
    };
  }, [language]);

  // Auto-scroll messages to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Text-to-Speech playback function
  const speakAudio = (textToSpeak) => {
    if (!synthRef.current) return;
    synthRef.current.cancel(); // Stop any active speech

    if (!textToSpeak) return;
    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    // Detect Tamil language or select voice
    const isTamil = /[\u0B80-\u0BFF]/.test(textToSpeak) || language === "ta";
    if (isTamil) {
      utterance.lang = "ta-IN";
    } else {
      utterance.lang = "en-US";
    }

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    synthRef.current.speak(utterance);
  };

  const stopSpeaking = () => {
    if (synthRef.current) {
      synthRef.current.cancel();
      setIsSpeaking(false);
    }
  };

  const toggleListening = () => {
    if (!speechSupported) {
      alert("Voice recognition is not supported in this browser. Please use Chrome, Edge, or Safari.");
      return;
    }
    stopSpeaking();

    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else {
      try {
        if (recognitionRef.current) {
          recognitionRef.current.lang = language === "ta" ? "ta-IN" : "en-US";
          recognitionRef.current.start();
        }
      } catch (e) {
        console.warn("Error starting mic:", e);
      }
    }
  };

  const handleSendMessage = async (userText, isFromVoice = false) => {
    const textToSend = userText || inputText;
    if (!textToSend.trim() || loading) return;

    setInputText("");
    const userMsgObj = {
      sender: "user",
      text: textToSend,
      isVoice: isFromVoice,
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsgObj]);
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: textToSend,
          is_voice: isFromVoice,
          language: language,
          prediction_context: result || {},
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const buddyMsgObj = {
          sender: "buddy",
          text: data.reply_text,
          speakText: data.speak_text,
          provider: data.provider,
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };
        setMessages((prev) => [...prev, buddyMsgObj]);

        // If user asked in VOICE, speak the answer aloud in VOICE!
        if (isFromVoice && data.speak_text) {
          speakAudio(data.speak_text);
        }
      } else {
        throw new Error("Chat response not ok");
      }
    } catch (err) {
      console.warn("Chat error, using local fallback response:", err);
      const fallbackText =
        result && result.prediction_class !== undefined
          ? `Your screening is classified as Class ${result.prediction_class} (${result.prediction || "DR"}). For this severity, regular follow-up and strict blood sugar control are strongly advised.`
          : "I am having trouble connecting to the network right now. Please consult your physician for full diagnosis details.";

      const buddyMsgObj = {
        sender: "buddy",
        text: fallbackText,
        speakText: fallbackText,
        provider: "offline-rule-engine",
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, buddyMsgObj]);
      if (isFromVoice) speakAudio(fallbackText);
    } finally {
      setLoading(false);
    }
  };

  const pClass = result?.prediction_class ?? result?.class_index ?? 0;
  const pName = result?.prediction || result?.class_name || `Class ${pClass}`;
  const pConf = Math.round((result?.confidence || 0) * 100);
  const pRisk = result?.risk_level || "Clinical";

  const quickChips = [
    `What does Class ${pClass} mean?`,
    "Explain the red dots (microaneurysms)",
    "When should I see an ophthalmologist?",
    "Diet and blood sugar recommendations",
    "தமிழில் விளக்குங்கள் (Explain in Tamil)",
  ];

  return (
    <>
      {/* Floating Action Button (FAB) at bottom-right */}
      <div
        className="voice-ai-buddy-container"
        style={{
          position: "fixed",
          bottom: "28px",
          right: "28px",
          zIndex: 9999,
          display: "flex",
          alignItems: "center",
          gap: "10px",
        }}
      >
        {!isOpen && (
          <div
            onClick={() => setIsOpen(true)}
            style={{
              background: "#ffffff",
              color: "#0284c7",
              padding: "8px 14px",
              borderRadius: "20px",
              fontSize: "13px",
              fontWeight: "700",
              boxShadow: "0 4px 15px rgba(2, 132, 199, 0.25)",
              border: "1.5px solid #bae6fd",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              transition: "transform 0.2s",
            }}
          >
            <span>✨</span>
            <span>Ask Buddy (VoiceAI)</span>
          </div>
        )}

        <button
          onClick={() => {
            if (isOpen) stopSpeaking();
            setIsOpen(!isOpen);
          }}
          style={{
            width: "58px",
            height: "58px",
            borderRadius: "50%",
            background: "linear-gradient(135deg, #0284c7 0%, #0369a1 100%)",
            color: "#ffffff",
            border: "none",
            boxShadow: "0 6px 20px rgba(2, 132, 199, 0.4)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "24px",
            transition: "all 0.2s ease",
            position: "relative",
          }}
          title="VoiceAI Assistant (Buddy)"
        >
          {isOpen ? "✕" : "🤖"}
          {/* Active green presence dot */}
          <span
            style={{
              position: "absolute",
              top: "3px",
              right: "3px",
              width: "14px",
              height: "14px",
              borderRadius: "50%",
              background: isSpeaking ? "#f59e0b" : "#22c55e",
              border: "2px solid #ffffff",
            }}
          />
        </button>
      </div>

      {/* Floating Chat Modal Window */}
      {isOpen && (
        <div
          className="voice-ai-buddy-container"
          style={{
            position: "fixed",
            bottom: "96px",
            right: "28px",
            width: "390px",
            maxWidth: "calc(100vw - 36px)",
            height: "580px",
            maxHeight: "calc(100vh - 120px)",
            background: "#ffffff",
            borderRadius: "16px",
            boxShadow: "0 12px 40px rgba(15, 23, 42, 0.22)",
            border: "1px solid #e2e8f0",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            zIndex: 9999,
            fontFamily: "Inter, system-ui, sans-serif",
          }}
        >
          {/* Header Bar */}
          <div
            style={{
              background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
              color: "#ffffff",
              padding: "14px 16px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "10px",
                  background: "#0284c7",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "18px",
                }}
              >
                🤖
              </div>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <strong style={{ fontSize: "15px", color: "#f8fafc" }}>Buddy</strong>
                  <span
                    style={{
                      fontSize: "10px",
                      background: "#0284c7",
                      color: "#ffffff",
                      padding: "1px 6px",
                      borderRadius: "4px",
                      fontWeight: "700",
                    }}
                  >
                    VoiceAI
                  </span>
                </div>
                <span style={{ fontSize: "11px", color: "#94a3b8" }}>
                  Powered by Gemini & VisionX
                </span>
              </div>
            </div>

            {/* Language & Sound Toggle */}
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                style={{
                  background: "#334155",
                  color: "#f8fafc",
                  border: "none",
                  borderRadius: "6px",
                  fontSize: "11px",
                  padding: "4px 6px",
                  cursor: "pointer",
                }}
              >
                <option value="auto">🌐 Auto</option>
                <option value="en">🇬🇧 English</option>
                <option value="ta">🇮🇳 தமிழ்</option>
              </select>

              {isSpeaking && (
                <button
                  onClick={stopSpeaking}
                  style={{
                    background: "#ef4444",
                    color: "white",
                    border: "none",
                    borderRadius: "6px",
                    padding: "4px 8px",
                    fontSize: "11px",
                    fontWeight: "600",
                    cursor: "pointer",
                  }}
                  title="Stop voice playback"
                >
                  ⏹ Stop
                </button>
              )}
            </div>
          </div>

          {/* Diagnostic Context Banner */}
          <div
            style={{
              background: "#f0f9ff",
              borderBottom: "1px solid #bae6fd",
              padding: "8px 14px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              fontSize: "12px",
            }}
          >
            <div>
              <span style={{ color: "#0369a1", fontWeight: "700" }}>Screening Focus:</span>{" "}
              <strong style={{ color: "#0f172a" }}>Class {pClass} ({pName})</strong>
            </div>
            <span
              style={{
                fontSize: "11px",
                fontWeight: "700",
                background: "#ffffff",
                color: "#0284c7",
                padding: "2px 6px",
                borderRadius: "4px",
                border: "1px solid #bfdbfe",
              }}
            >
              {pConf}% Conf
            </span>
          </div>

          {/* Message History Thread */}
          <div
            style={{
              flex: "1",
              padding: "14px",
              overflowY: "auto",
              background: "#f8fafc",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
            }}
          >
            {messages.map((msg, idx) => (
              <div
                key={idx}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: msg.sender === "user" ? "flex-end" : "flex-start",
                }}
              >
                <div
                  style={{
                    maxWidth: "84%",
                    padding: "10px 14px",
                    borderRadius: msg.sender === "user" ? "14px 14px 2px 14px" : "14px 14px 14px 2px",
                    background: msg.sender === "user" ? "#0284c7" : "#ffffff",
                    color: msg.sender === "user" ? "#ffffff" : "#0f172a",
                    border: msg.sender === "user" ? "none" : "1px solid #e2e8f0",
                    boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
                    fontSize: "13.5px",
                    lineHeight: "1.5",
                    position: "relative",
                  }}
                >
                  {/* Voice input badge if asked via mic */}
                  {msg.isVoice && (
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "3px",
                        fontSize: "10.5px",
                        background: "rgba(255,255,255,0.25)",
                        padding: "1px 6px",
                        borderRadius: "4px",
                        marginBottom: "4px",
                      }}
                    >
                      🎤 Voice Question
                    </span>
                  )}

                  <div style={{ whiteSpace: "pre-wrap" }}>{msg.text}</div>

                  {/* Speaker Button on Buddy messages */}
                  {msg.sender === "buddy" && (
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "flex-end",
                        marginTop: "6px",
                        gap: "6px",
                      }}
                    >
                      <button
                        onClick={() => speakAudio(msg.speakText || msg.text)}
                        style={{
                          background: "transparent",
                          border: "none",
                          color: "#0284c7",
                          cursor: "pointer",
                          fontSize: "14px",
                          padding: "2px 4px",
                        }}
                        title="Listen to answer"
                      >
                        🔊
                      </button>
                    </div>
                  )}
                </div>
                <span
                  style={{
                    fontSize: "10px",
                    color: "#94a3b8",
                    marginTop: "3px",
                    marginRight: msg.sender === "user" ? "4px" : 0,
                    marginLeft: msg.sender === "buddy" ? "4px" : 0,
                  }}
                >
                  {msg.time}
                </span>
              </div>
            ))}

            {loading && (
              <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#64748b", fontSize: "12.5px" }}>
                <span>🤖</span>
                <span>Buddy is thinking...</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick Action Suggestion Chips */}
          <div
            style={{
              padding: "6px 12px",
              background: "#ffffff",
              borderTop: "1px solid #f1f5f9",
              overflowX: "auto",
              whiteSpace: "nowrap",
              display: "flex",
              gap: "6px",
            }}
          >
            {quickChips.map((chip, idx) => (
              <button
                key={idx}
                onClick={() => handleSendMessage(chip, false)}
                style={{
                  background: "#f1f5f9",
                  border: "1px solid #e2e8f0",
                  borderRadius: "14px",
                  padding: "4px 10px",
                  fontSize: "11.5px",
                  color: "#334155",
                  cursor: "pointer",
                  flexShrink: 0,
                }}
              >
                {chip}
              </button>
            ))}
          </div>

          {/* Voice Listening Active Waveform Banner */}
          {isListening && (
            <div
              style={{
                background: "#fef2f2",
                borderTop: "1px solid #fecaca",
                padding: "8px 14px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                color: "#dc2626",
                fontSize: "12px",
                fontWeight: "600",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontSize: "16px", animation: "pulse 1s infinite" }}>🎙️</span>
                <span>Listening... Speak your question now</span>
              </div>
              <button
                onClick={toggleListening}
                style={{
                  background: "#dc2626",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: "4px",
                  padding: "2px 8px",
                  fontSize: "11px",
                  cursor: "pointer",
                }}
              >
                Cancel
              </button>
            </div>
          )}

          {/* Bottom Input Form */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage(inputText, false);
            }}
            style={{
              padding: "10px 12px",
              background: "#ffffff",
              borderTop: "1px solid #e2e8f0",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            {/* Microphone Button */}
            <button
              type="button"
              onClick={toggleListening}
              style={{
                width: "38px",
                height: "38px",
                borderRadius: "50%",
                background: isListening ? "#ef4444" : "#f1f5f9",
                color: isListening ? "#ffffff" : "#0284c7",
                border: "1px solid #cbd5e1",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "18px",
                transition: "all 0.15s ease",
              }}
              title={isListening ? "Stop Listening" : "Ask by Voice"}
            >
              🎤
            </button>

            {/* Text Input */}
            <input
              type="text"
              placeholder={isListening ? "Listening..." : "Type or speak question..."}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              style={{
                flex: "1",
                padding: "9px 12px",
                border: "1.5px solid #cbd5e1",
                borderRadius: "20px",
                fontSize: "13px",
                outline: "none",
              }}
            />

            {/* Send Button */}
            <button
              type="submit"
              disabled={!inputText.trim() || loading}
              style={{
                width: "38px",
                height: "38px",
                borderRadius: "50%",
                background: inputText.trim() ? "#0284c7" : "#e2e8f0",
                color: inputText.trim() ? "#ffffff" : "#94a3b8",
                border: "none",
                cursor: inputText.trim() ? "pointer" : "default",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "15px",
                transition: "all 0.15s ease",
              }}
            >
              ➤
            </button>
          </form>
        </div>
      )}
    </>
  );
}
