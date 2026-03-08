import React, { useState, useEffect } from 'react';
import {
  Upload, FileText, Globe, AlertCircle, Scale, ChevronRight,
  BookOpen, Users, Clock, HelpCircle, Volume2, Sparkles, X, Check, Info, Cpu, Zap
} from 'lucide-react';

// ─── API helpers ──────────────────────────────────────────────────────────────

/**
 * Call the backend /api/explain-document endpoint.
 * Returns the full ExplanationResponse object (including the `source` field).
 * Throws on HTTP error so the caller can catch and show an error state.
 */
async function callExplainAPI(text, language) {
  const response = await fetch(`${import.meta.env.VITE_API_URL}/api/explain-document`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, language }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Server error ${response.status}`);
  }

  return response.json();
}

/**
 * Upload a PDF to /api/upload-pdf and get the extracted text back.
 * Returns { text, documentType, pageCount }.
 */
async function callUploadPDF(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${import.meta.env.VITE_API_URL}/api/upload-pdf`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Upload error ${response.status}`);
  }

  return response.json();
}

// ─── Sample document ──────────────────────────────────────────────────────────
const sampleFIR = `FIRST INFORMATION REPORT
(Under Section 154 Cr.P.C.)

Police Station: Connaught Place Police Station
District: New Delhi
State: Delhi
Date: 15th October 2024
FIR No: 234/2024

COMPLAINANT DETAILS:
Name: Rajesh Kumar
Age: 45 years
Address: 123, Janpath Road, New Delhi
Occupation: Businessman

ACCUSED DETAILS:
Name: Amit Sharma
Address: 456, Lodhi Road, New Delhi

DETAILS OF OFFENCE:
Sections of Law: IPC Section 420 (Cheating), Section 406 (Criminal Breach of Trust)

BRIEF FACTS:
The complainant states that the accused Amit Sharma approached him in June 2024 with a
business proposal to invest in a real estate project. The complainant invested
Rs. 25,00,000/- (Twenty Five Lakhs) based on false promises and forged documents shown
by the accused.

Despite repeated requests, the accused has neither returned the invested amount nor
provided any returns on investment. The accused has been avoiding the complainant and
has stopped responding to calls and messages since August 2024.

The complainant has submitted copies of bank transfer receipts, WhatsApp conversations,
and email communications as evidence.

Action Taken: Case registered under IPC Section 420 and 406. Investigation assigned to
Inspector Sharma.`;

// ─── Source badge component ───────────────────────────────────────────────────
// Shows whether the explanation came from the fine-tuned LLM or the fallback.
function SourceBadge({ source, language }) {
  const isLLM = source === 'llm';
  return (
    <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full font-bold text-sm shadow-md ${
      isLLM
        ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white'
        : 'bg-gradient-to-r from-blue-500 to-indigo-500 text-white'
    }`}>
      {isLLM ? <Cpu className="w-4 h-4" /> : <Zap className="w-4 h-4" />}
      {isLLM
        ? (language === 'hindi' ? 'फाइन-ट्यून्ड AI मॉडल' : 'Fine-tuned AI Model')
        : (language === 'hindi' ? 'नियम-आधारित व्याख्या' : 'Rule-based Explanation')}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function NyayaGPTLite() {
  const [step, setStep] = useState(1);
  const [documentText, setDocumentText] = useState('');
  const [selectedLanguage, setSelectedLanguage] = useState('english');
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStage, setProcessingStage] = useState('');
  const [explanation, setExplanation] = useState(null);
  const [uploadMethod, setUploadMethod] = useState('paste');
  const [showDisclaimer, setShowDisclaimer] = useState(true);
  const [documentType, setDocumentType] = useState(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [apiError, setApiError] = useState(null);
  const [inferenceSource, setInferenceSource] = useState(null); // "llm" | "fallback"

  // ── Process document via real backend API ───────────────────────────────────
  const processDocument = async (text) => {
    setIsProcessing(true);
    setApiError(null);
    setProcessingStage(selectedLanguage === 'hindi' ? 'दस्तावेज़ भेजा जा रहा है...' : 'Sending document to AI...');

    try {
      // Small UI delay so the processing overlay is visible before the request fires
      await new Promise(resolve => setTimeout(resolve, 400));

      setProcessingStage(
        selectedLanguage === 'hindi'
          ? 'AI मॉडल विश्लेषण कर रहा है...'
          : 'AI model is analysing...'
      );

      // ── Real API call ───────────────────────────────────────────────────────
      const data = await callExplainAPI(text, selectedLanguage);
      // data = ExplanationResponse: { source, summary, parties, stage,
      //         nextSteps, options, highlightedSections, timeline,
      //         suggestedQuestions, documentType }

      setExplanation(data);
      setDocumentType(data.documentType);
      setInferenceSource(data.source); // "llm" or "fallback"
      setStep(3);

    } catch (err) {
      // Network error, server crash, validation error, etc.
      setApiError(
        selectedLanguage === 'hindi'
          ? `त्रुटि: ${err.message}`
          : `Error: ${err.message}`
      );
    } finally {
      setIsProcessing(false);
      setProcessingStage('');
    }
  };

  // ── Handle PDF upload ───────────────────────────────────────────────────────
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setIsProcessing(true);
    setProcessingStage(
      selectedLanguage === 'hindi' ? 'PDF से टेक्स्ट निकाला जा रहा है...' : 'Extracting text from PDF...'
    );
    setApiError(null);

    try {
      const result = await callUploadPDF(file);
      setDocumentText(result.text);
      // Advance to step 2 so user can review extracted text before submitting
      setStep(2);
    } catch (err) {
      setApiError(
        selectedLanguage === 'hindi'
          ? `PDF त्रुटि: ${err.message}`
          : `PDF error: ${err.message}`
      );
    } finally {
      setIsProcessing(false);
      setProcessingStage('');
    }
  };

  // ── Text-to-speech (browser Web Speech API) ─────────────────────────────────
  const playExplanation = () => {
    if (isPlayingAudio) {
      window.speechSynthesis.cancel();
      setIsPlayingAudio(false);
      return;
    }

    if (!explanation?.summary) return;

    const utterance = new SpeechSynthesisUtterance(explanation.summary);
    utterance.lang = selectedLanguage === 'hindi' ? 'hi-IN' : 'en-IN';
    utterance.onend = () => setIsPlayingAudio(false);
    utterance.onerror = () => setIsPlayingAudio(false);

    setIsPlayingAudio(true);
    window.speechSynthesis.speak(utterance);
  };

  // ── Helpers for rendering parties ──────────────────────────────────────────
  // The LLM returns a free-form parties dict; the fallback has known keys.
  // Render whatever keys exist.
  const renderParties = (parties) => {
    if (!parties) return null;

    // Known key → label mapping
    const labelMap = {
      complainant: selectedLanguage === 'hindi' ? 'शिकायतकर्ता' : 'Complainant',
      accused:     selectedLanguage === 'hindi' ? 'आरोपी' : 'Accused',
      petitioner:  selectedLanguage === 'hindi' ? 'याचिकाकर्ता' : 'Petitioner',
      respondent:  selectedLanguage === 'hindi' ? 'प्रतिवादी' : 'Respondent',
      sender:      selectedLanguage === 'hindi' ? 'भेजने वाला' : 'Sender',
      recipient:   selectedLanguage === 'hindi' ? 'प्राप्तकर्ता' : 'Recipient',
    };

    const colorMap = {
      complainant: 'green', petitioner: 'green', sender: 'green',
      accused:     'red',   respondent: 'red',   recipient: 'amber',
    };

    return Object.entries(parties).map(([key, value]) => {
      const color = colorMap[key] || 'blue';
      return (
        <div key={key} className={`p-4 bg-${color}-50 rounded-lg border-l-4 border-${color}-600`}>
          <p className={`font-semibold text-${color}-900 mb-1`}>
            {labelMap[key] || key}:
          </p>
          <p className="text-gray-700">{value}</p>
        </div>
      );
    });
  };

  // ────────────────────────────────────────────────────────────────────────────
  // RENDER
  // ────────────────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-orange-50 to-red-50 font-sans">

      {/* Disclaimer Banner */}
      {showDisclaimer && (
        <div className="bg-gradient-to-r from-red-900 to-orange-900 text-white py-3 px-4 shadow-lg relative">
          <div className="max-w-6xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-3 flex-1">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <p className="text-sm font-medium">
                {selectedLanguage === 'hindi'
                  ? 'यह केवल समझने के लिए है। यह कानूनी सलाह नहीं है। महत्वपूर्ण निर्णय के लिए वकील से परामर्श करें।'
                  : 'This tool provides simplified explanations only. Not legal advice. Consult a lawyer for important decisions.'}
              </p>
            </div>
            <button onClick={() => setShowDisclaimer(false)} className="ml-4 p-1 hover:bg-white/20 rounded transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Real-World Impact Story */}
      {step === 1 && (
        <div className="bg-gradient-to-r from-green-600 to-emerald-600 text-white py-6 px-4">
          <div className="max-w-6xl mx-auto">
            <div className="flex items-start gap-4">
              <div className="bg-white/20 p-3 rounded-lg flex-shrink-0">
                <Sparkles className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-bold text-lg mb-2">
                  {selectedLanguage === 'hindi' ? '🌾 वास्तविक प्रभाव' : '🌾 Real-World Impact'}
                </h3>
                <p className="text-sm leading-relaxed">
                  {selectedLanguage === 'hindi'
                    ? 'एक किसान को कानूनी नोटिस मिला। वह समझ नहीं पाया। NyayaGPT Lite ने हिंदी में समझाया कि उसके पास 15 दिन हैं, और कानूनी सहायता उपलब्ध है।'
                    : "A farmer received a legal notice. He didn't understand it. NyayaGPT Lite explained in Hindi that he had 15 days to respond and suggested legal aid. He responded on time."}
                </p>
                <div className="mt-3 flex items-center gap-4 text-xs">
                  <span className="bg-white/20 px-3 py-1 rounded-full">{selectedLanguage === 'hindi' ? '₹3,000 बचाया' : '₹3,000 Saved'}</span>
                  <span className="bg-white/20 px-3 py-1 rounded-full">{selectedLanguage === 'hindi' ? '2 दिन का समय बचाया' : '2 Days Saved'}</span>
                  <span className="bg-white/20 px-3 py-1 rounded-full">{selectedLanguage === 'hindi' ? 'अनावश्यक चिंता टली' : 'Unnecessary Worry Avoided'}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="border-b-4 border-orange-800 bg-white/80 backdrop-blur-sm sticky top-0 z-40 shadow-md">
        <div className="max-w-6xl mx-auto px-6 py-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-gradient-to-br from-orange-600 to-red-600 p-3 rounded-xl shadow-lg">
                <Scale className="w-8 h-8 text-white" />
              </div>
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-3xl font-bold text-gray-900" style={{ fontFamily: 'Georgia, serif' }}>
                    NyayaGPT Lite
                  </h1>
                  {/* Replaced hardcoded DEMO MODE badge with live inference source indicator */}
                  {inferenceSource ? (
                    <SourceBadge source={inferenceSource} language={selectedLanguage} />
                  ) : (
                    <span className="bg-emerald-100 text-emerald-700 text-xs font-bold px-3 py-1 rounded-full">
                      {selectedLanguage === 'hindi' ? 'AI सक्रिय' : 'AI READY'}
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-600 font-medium">
                  {selectedLanguage === 'hindi' ? 'सरल भाषा में कानूनी दस्तावेज़' : 'Legal Documents in Simple Language'}
                </p>
              </div>
            </div>

            {/* Language Toggle */}
            <div className="flex items-center gap-2 bg-orange-100 p-1.5 rounded-lg">
              <button
                onClick={() => setSelectedLanguage('english')}
                className={`px-4 py-2 rounded-md font-semibold transition-all ${
                  selectedLanguage === 'english' ? 'bg-white text-orange-700 shadow-md' : 'text-gray-600 hover:text-orange-700'
                }`}
              >
                English
              </button>
              <button
                onClick={() => setSelectedLanguage('hindi')}
                className={`px-4 py-2 rounded-md font-semibold transition-all ${
                  selectedLanguage === 'hindi' ? 'bg-white text-orange-700 shadow-md' : 'text-gray-600 hover:text-orange-700'
                }`}
              >
                हिंदी
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Progress Steps */}
      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="flex items-center justify-center gap-2 mb-8">
          {[1, 2, 3, 4].map((num) => (
            <React.Fragment key={num}>
              <div className="flex items-center">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold transition-all ${
                  step >= num
                    ? 'bg-gradient-to-br from-orange-600 to-red-600 text-white shadow-lg scale-110'
                    : 'bg-gray-200 text-gray-500'
                }`}>
                  {step > num ? <Check className="w-5 h-5" /> : num}
                </div>
              </div>
              {num < 4 && (
                <div className={`w-16 h-1 transition-all ${
                  step > num ? 'bg-gradient-to-r from-orange-600 to-red-600' : 'bg-gray-300'
                }`} />
              )}
            </React.Fragment>
          ))}
        </div>

        {/* ── Error banner (shown if API call fails) ──────────────────────── */}
        {apiError && (
          <div className="max-w-3xl mx-auto mb-6 p-4 bg-red-50 border-2 border-red-300 rounded-xl flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-bold text-red-800">
                {selectedLanguage === 'hindi' ? 'अनुरोध विफल हुआ' : 'Request failed'}
              </p>
              <p className="text-sm text-red-700 mt-1">{apiError}</p>
              <p className="text-xs text-red-600 mt-2">
                {selectedLanguage === 'hindi'
                  ? 'सुनिश्चित करें कि बैकएंड सर्वर चल रहा है: python main.py'
                  : 'Make sure the backend server is running: python main.py'}
              </p>
            </div>
          </div>
        )}

        {/* ── STEP 1: Upload / Paste ──────────────────────────────────────── */}
        {step === 1 && (
          <div className="max-w-3xl mx-auto">
            <div className="mb-6 bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl p-6 border-2 border-green-300 shadow-lg">
              <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-green-600" />
                {selectedLanguage === 'hindi' ? 'त्वरित प्रभाव' : 'Quick Impact'}
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="flex items-start gap-2">
                  <Clock className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-bold text-gray-900">{selectedLanguage === 'hindi' ? '~2-3 वकील विज़िट बचाता है' : 'Saves ~2-3 lawyer visits'}</p>
                    <p className="text-xs text-gray-600">{selectedLanguage === 'hindi' ? 'बुनियादी समझ के लिए' : 'for basic understanding'}</p>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <FileText className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-bold text-gray-900">{selectedLanguage === 'hindi' ? 'सेकंड में व्याख्या' : 'Explains in seconds'}</p>
                    <p className="text-xs text-gray-600">{selectedLanguage === 'hindi' ? 'तुरंत स्पष्टता' : 'instant clarity'}</p>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <Globe className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-bold text-gray-900">{selectedLanguage === 'hindi' ? 'अंग्रेजी और हिंदी' : 'English & Hindi'}</p>
                    <p className="text-xs text-gray-600">{selectedLanguage === 'hindi' ? 'आपकी भाषा में' : 'in your language'}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-2xl shadow-2xl p-8 border-2 border-orange-200">
              <div className="text-center mb-8">
                <h2 className="text-3xl font-bold text-gray-900 mb-3" style={{ fontFamily: 'Georgia, serif' }}>
                  {selectedLanguage === 'hindi' ? 'अपना कानूनी दस्तावेज़ अपलोड करें' : 'Upload Your Legal Document'}
                </h2>
                <p className="text-gray-600">
                  {selectedLanguage === 'hindi'
                    ? 'FIR, कोर्ट आदेश, या कानूनी नोटिस अपलोड करें या पेस्ट करें'
                    : 'Upload or paste an FIR, Court Order, or Legal Notice'}
                </p>
              </div>

              {/* Upload Method Toggle */}
              <div className="flex gap-4 mb-6">
                <button
                  onClick={() => setUploadMethod('paste')}
                  className={`flex-1 py-3 px-4 rounded-xl font-semibold transition-all flex items-center justify-center gap-2 ${
                    uploadMethod === 'paste' ? 'bg-gradient-to-r from-orange-600 to-red-600 text-white shadow-lg' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  <FileText className="w-5 h-5" />
                  {selectedLanguage === 'hindi' ? 'टेक्स्ट पेस्ट करें' : 'Paste Text'}
                </button>
                <button
                  onClick={() => setUploadMethod('upload')}
                  className={`flex-1 py-3 px-4 rounded-xl font-semibold transition-all flex items-center justify-center gap-2 ${
                    uploadMethod === 'upload' ? 'bg-gradient-to-r from-orange-600 to-red-600 text-white shadow-lg' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  <Upload className="w-5 h-5" />
                  {selectedLanguage === 'hindi' ? 'PDF अपलोड करें' : 'Upload PDF'}
                </button>
              </div>

              {/* Input Area */}
              {uploadMethod === 'paste' ? (
                <div className="mb-6">
                  <textarea
                    value={documentText}
                    onChange={(e) => setDocumentText(e.target.value)}
                    placeholder={selectedLanguage === 'hindi' ? 'अपने दस्तावेज़ का टेक्स्ट यहाँ पेस्ट करें...' : 'Paste your document text here...'}
                    className="w-full h-64 p-4 border-2 border-orange-300 rounded-xl focus:outline-none focus:ring-4 focus:ring-orange-200 focus:border-orange-500 transition-all resize-none font-mono text-sm"
                  />
                  <div className="mt-3 flex justify-between items-center">
                    <button
                      onClick={() => setDocumentText(sampleFIR)}
                      className="text-orange-600 hover:text-orange-700 font-semibold text-sm flex items-center gap-1"
                    >
                      <Sparkles className="w-4 h-4" />
                      {selectedLanguage === 'hindi' ? 'नमूना FIR आज़माएं' : 'Try Sample FIR'}
                    </button>
                    <span className="text-sm text-gray-500">
                      {documentText.length} {selectedLanguage === 'hindi' ? 'अक्षर' : 'characters'}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="mb-6">
                  <label className="block">
                    <div className="border-4 border-dashed border-orange-300 rounded-xl p-12 text-center hover:border-orange-500 hover:bg-orange-50/50 transition-all cursor-pointer">
                      <Upload className="w-16 h-16 mx-auto mb-4 text-orange-600" />
                      <p className="text-lg font-semibold text-gray-700 mb-2">
                        {selectedLanguage === 'hindi' ? 'PDF फ़ाइल अपलोड करने के लिए क्लिक करें' : 'Click to Upload PDF File'}
                      </p>
                      <p className="text-sm text-gray-500">
                        {selectedLanguage === 'hindi' ? 'या फ़ाइल को यहाँ खींचें' : 'or drag and drop file here'}
                      </p>
                      <p className="text-xs text-gray-400 mt-2">
                        {selectedLanguage === 'hindi'
                          ? 'टेक्स्ट निकाला जाएगा और समीक्षा के लिए दिखाया जाएगा'
                          : 'Text will be extracted and shown for review'}
                      </p>
                    </div>
                    <input type="file" accept=".pdf" onChange={handleFileUpload} className="hidden" />
                  </label>
                </div>
              )}

              <button
                onClick={() => { if (documentText.trim()) setStep(2); }}
                disabled={!documentText.trim()}
                className={`w-full py-4 rounded-xl font-bold text-lg transition-all flex items-center justify-center gap-2 ${
                  documentText.trim()
                    ? 'bg-gradient-to-r from-orange-600 to-red-600 text-white hover:shadow-2xl hover:scale-105 active:scale-95'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                }`}
              >
                {selectedLanguage === 'hindi' ? 'आगे बढ़ें' : 'Continue'}
                <ChevronRight className="w-6 h-6" />
              </button>
            </div>
          </div>
        )}

        {/* ── STEP 2: Confirm & Process ───────────────────────────────────── */}
        {step === 2 && (
          <div className="max-w-3xl mx-auto">
            <div className="bg-white rounded-2xl shadow-2xl p-8 border-2 border-orange-200">
              <div className="text-center mb-8">
                <h2 className="text-3xl font-bold text-gray-900 mb-3" style={{ fontFamily: 'Georgia, serif' }}>
                  {selectedLanguage === 'hindi' ? 'दस्तावेज़ की पुष्टि करें' : 'Confirm Document'}
                </h2>
                <p className="text-gray-600">
                  {selectedLanguage === 'hindi' ? 'दस्तावेज़ का पूर्वावलोकन और प्रक्रिया शुरू करें' : 'Preview your document and start processing'}
                </p>
              </div>

              <div className="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 mb-6 max-h-96 overflow-y-auto border-2 border-orange-200">
                <pre className="whitespace-pre-wrap text-sm text-gray-800 font-mono">{documentText}</pre>
              </div>

              <div className="flex gap-4">
                <button
                  onClick={() => setStep(1)}
                  className="flex-1 py-3 px-4 rounded-xl font-semibold bg-gray-200 text-gray-700 hover:bg-gray-300 transition-all"
                >
                  {selectedLanguage === 'hindi' ? 'वापस जाएं' : 'Go Back'}
                </button>
                <button
                  onClick={() => processDocument(documentText)}
                  className="flex-1 py-4 rounded-xl font-bold text-lg bg-gradient-to-r from-orange-600 to-red-600 text-white hover:shadow-2xl hover:scale-105 active:scale-95 transition-all flex items-center justify-center gap-2"
                >
                  <Sparkles className="w-5 h-5" />
                  {selectedLanguage === 'hindi' ? 'AI व्याख्या प्राप्त करें' : 'Get AI Explanation'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── STEP 3: AI Explanation ──────────────────────────────────────── */}
        {step === 3 && explanation && (
          <div className="max-w-5xl mx-auto">
            {/* Document type + source badges */}
            <div className="mb-6 flex items-center justify-center gap-3 flex-wrap">
              {documentType && (
                <span className="inline-flex items-center gap-2 bg-gradient-to-r from-orange-600 to-red-600 text-white px-6 py-2 rounded-full font-bold shadow-lg">
                  <FileText className="w-5 h-5" />
                  {selectedLanguage === 'hindi' ? 'पहचाना गया: ' : 'Detected: '}
                  {documentType === 'FIR' ? 'FIR'
                    : documentType === 'COURT_ORDER' ? (selectedLanguage === 'hindi' ? 'कोर्ट आदेश' : 'Court Order')
                    : documentType === 'LEGAL_NOTICE' ? (selectedLanguage === 'hindi' ? 'कानूनी नोटिस' : 'Legal Notice')
                    : documentType}
                </span>
              )}
              {inferenceSource && <SourceBadge source={inferenceSource} language={selectedLanguage} />}
            </div>

            <div className="bg-white rounded-2xl shadow-2xl p-8 border-2 border-orange-200 mb-6">
              <div className="flex items-center justify-between mb-8">
                <h2 className="text-3xl font-bold text-gray-900" style={{ fontFamily: 'Georgia, serif' }}>
                  {selectedLanguage === 'hindi' ? 'AI व्याख्या' : 'AI Explanation'}
                </h2>
                <button
                  onClick={playExplanation}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold transition-all ${
                    isPlayingAudio ? 'bg-red-600 text-white' : 'bg-orange-100 text-orange-700 hover:bg-orange-200'
                  }`}
                >
                  <Volume2 className="w-5 h-5" />
                  {isPlayingAudio
                    ? (selectedLanguage === 'hindi' ? 'बज रहा है...' : 'Playing...')
                    : (selectedLanguage === 'hindi' ? 'सुनें' : 'Listen')}
                </button>
              </div>

              {/* Case Summary */}
              <div className="mb-8 p-6 bg-gradient-to-br from-orange-50 to-red-50 rounded-xl border-2 border-orange-200">
                <div className="flex items-start gap-3 mb-3">
                  <div className="bg-orange-600 p-2 rounded-lg"><BookOpen className="w-6 h-6 text-white" /></div>
                  <h3 className="text-xl font-bold text-gray-900">{selectedLanguage === 'hindi' ? 'मामले का सारांश' : 'Case Summary'}</h3>
                </div>
                <p className="text-gray-800 leading-relaxed text-lg">{explanation.summary}</p>
              </div>

              {/* Parties */}
              {explanation.parties && Object.keys(explanation.parties).length > 0 && (
                <div className="mb-8 p-6 bg-white rounded-xl border-2 border-orange-200">
                  <div className="flex items-start gap-3 mb-4">
                    <div className="bg-red-600 p-2 rounded-lg"><Users className="w-6 h-6 text-white" /></div>
                    <h3 className="text-xl font-bold text-gray-900">{selectedLanguage === 'hindi' ? 'पक्षकार' : 'Parties Involved'}</h3>
                  </div>
                  <div className="space-y-3">{renderParties(explanation.parties)}</div>
                </div>
              )}

              {/* Current Stage */}
              <div className="mb-8 p-6 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border-2 border-blue-200">
                <div className="flex items-start gap-3 mb-3">
                  <div className="bg-blue-600 p-2 rounded-lg"><Info className="w-6 h-6 text-white" /></div>
                  <h3 className="text-xl font-bold text-gray-900">{selectedLanguage === 'hindi' ? 'वर्तमान स्थिति' : 'Current Stage'}</h3>
                </div>
                <p className="text-gray-800 leading-relaxed text-lg">{explanation.stage}</p>
              </div>

              {/* Legal Sections */}
              {explanation.highlightedSections && explanation.highlightedSections.length > 0 && (
                <div className="mb-8 p-6 bg-white rounded-xl border-2 border-orange-200">
                  <h3 className="text-xl font-bold text-gray-900 mb-4">{selectedLanguage === 'hindi' ? 'कानूनी धाराएं' : 'Legal Sections'}</h3>
                  <div className="space-y-3">
                    {explanation.highlightedSections.map((item, idx) => (
                      <div key={idx} className="p-4 bg-amber-50 rounded-lg border-l-4 border-amber-600">
                        <p className="font-bold text-amber-900 mb-1">{item.section}</p>
                        <p className="text-gray-700">{item.explanation}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* What Happens Next */}
              {explanation.nextSteps && explanation.nextSteps.length > 0 && (
                <div className="mb-8 p-6 bg-white rounded-xl border-2 border-orange-200">
                  <div className="flex items-start gap-3 mb-4">
                    <div className="bg-purple-600 p-2 rounded-lg"><Clock className="w-6 h-6 text-white" /></div>
                    <h3 className="text-xl font-bold text-gray-900">{selectedLanguage === 'hindi' ? 'आगे क्या होगा' : 'What Happens Next'}</h3>
                  </div>
                  <ol className="space-y-3">
                    {explanation.nextSteps.map((s, idx) => (
                      <li key={idx} className="flex items-start gap-3">
                        <span className="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-purple-600 to-pink-600 text-white rounded-full flex items-center justify-center font-bold">
                          {idx + 1}
                        </span>
                        <p className="text-gray-800 leading-relaxed pt-1">{s}</p>
                      </li>
                    ))}
                  </ol>
                  {explanation.timeline && (
                    <div className="mt-4 p-4 bg-purple-50 rounded-lg">
                      <p className="text-purple-900 font-semibold">⏱️ {explanation.timeline}</p>
                    </div>
                  )}
                </div>
              )}

              {/* Available Options */}
              {explanation.options && explanation.options.length > 0 && (
                <div className="mb-8">
                  <h3 className="text-xl font-bold text-gray-900 mb-4">{selectedLanguage === 'hindi' ? 'उपलब्ध विकल्प' : 'Available Options'}</h3>
                  <div className="grid gap-4">
                    {explanation.options.map((option, idx) => (
                      <div key={idx} className={`p-5 rounded-xl border-2 transition-all hover:shadow-lg ${
                        option.recommended ? 'bg-gradient-to-br from-green-50 to-emerald-50 border-green-300' : 'bg-gray-50 border-gray-300'
                      }`}>
                        {option.recommended && (
                          <div className="bg-green-600 text-white px-3 py-1 rounded-full text-xs font-bold inline-block mb-2">
                            {selectedLanguage === 'hindi' ? 'सुझाया गया' : 'RECOMMENDED'}
                          </div>
                        )}
                        <h4 className="font-bold text-lg text-gray-900">{option.title}</h4>
                        <p className="text-gray-700 mt-1">{option.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Suggested Questions */}
              {explanation.suggestedQuestions && explanation.suggestedQuestions.length > 0 && (
                <div className="p-6 bg-gradient-to-br from-orange-50 to-red-50 rounded-xl border-2 border-orange-200 mb-8">
                  <div className="flex items-start gap-3 mb-4">
                    <div className="bg-orange-600 p-2 rounded-lg"><HelpCircle className="w-6 h-6 text-white" /></div>
                    <h3 className="text-xl font-bold text-gray-900">{selectedLanguage === 'hindi' ? 'आप यह भी पूछ सकते हैं' : 'You May Also Ask'}</h3>
                  </div>
                  <div className="space-y-2">
                    {explanation.suggestedQuestions.map((q, idx) => (
                      <button key={idx} className="w-full text-left p-3 bg-white rounded-lg border-2 border-orange-200 hover:border-orange-400 hover:shadow-md transition-all">
                        <p className="text-gray-800">{q}</p>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Can / Cannot */}
              <div className="mb-8 p-6 bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl border-2 border-purple-200">
                <div className="flex items-start gap-3 mb-4">
                  <div className="bg-purple-600 p-2 rounded-lg"><AlertCircle className="w-6 h-6 text-white" /></div>
                  <h3 className="text-xl font-bold text-gray-900">
                    {selectedLanguage === 'hindi' ? '⚖️ यह AI क्या कर सकता है और क्या नहीं' : '⚖️ What This AI Can and Cannot Do'}
                  </h3>
                </div>
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="space-y-2 text-sm">
                    <h4 className="font-bold text-green-800 flex items-center gap-2"><Check className="w-4 h-4" />{selectedLanguage === 'hindi' ? 'कर सकता है:' : 'CAN:'}</h4>
                    {[
                      selectedLanguage === 'hindi' ? 'सरल भाषा में समझाना' : 'Explain in simple language',
                      selectedLanguage === 'hindi' ? 'कानूनी प्रक्रिया के चरण बताना' : 'Describe legal process steps',
                      selectedLanguage === 'hindi' ? 'उपलब्ध विकल्प सुझाना' : 'Suggest available options',
                    ].map((t, i) => <p key={i} className="flex gap-2 text-gray-700"><span className="text-green-600">✓</span>{t}</p>)}
                  </div>
                  <div className="space-y-2 text-sm">
                    <h4 className="font-bold text-red-800 flex items-center gap-2"><X className="w-4 h-4" />{selectedLanguage === 'hindi' ? 'नहीं कर सकता:' : 'CANNOT:'}</h4>
                    {[
                      selectedLanguage === 'hindi' ? 'मामले का परिणाम बताना' : 'Predict case outcomes',
                      selectedLanguage === 'hindi' ? 'कानूनी सलाह देना' : 'Give legal advice',
                      selectedLanguage === 'hindi' ? 'वकील की जगह लेना' : 'Replace a lawyer',
                    ].map((t, i) => <p key={i} className="flex gap-2 text-gray-700"><span className="text-red-600">✗</span>{t}</p>)}
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-4 mt-8">
                <button
                  onClick={() => { setStep(1); setDocumentText(''); setExplanation(null); setInferenceSource(null); setApiError(null); }}
                  className="flex-1 py-3 px-4 rounded-xl font-semibold bg-gray-200 text-gray-700 hover:bg-gray-300 transition-all"
                >
                  {selectedLanguage === 'hindi' ? 'नया दस्तावेज़' : 'New Document'}
                </button>
                <button
                  onClick={() => setStep(4)}
                  className="flex-1 py-3 px-4 rounded-xl font-semibold bg-gradient-to-r from-orange-600 to-red-600 text-white hover:shadow-lg transition-all flex items-center justify-center gap-2"
                >
                  {selectedLanguage === 'hindi' ? 'सहायता और संसाधन' : 'Help & Resources'}
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── STEP 4: Help & Resources (unchanged) ───────────────────────── */}
        {step === 4 && (
          <div className="max-w-4xl mx-auto">
            <div className="bg-white rounded-2xl shadow-2xl p-8 border-2 border-orange-200">
              <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center" style={{ fontFamily: 'Georgia, serif' }}>
                {selectedLanguage === 'hindi' ? 'सहायता और संसाधन' : 'Help & Resources'}
              </h2>
              <div className="grid gap-6">
                <div className="p-6 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border-2 border-blue-200">
                  <h3 className="text-xl font-bold text-gray-900 mb-3">{selectedLanguage === 'hindi' ? '📋 कानूनी सहायता' : '📋 Legal Aid'}</h3>
                  <ul className="space-y-2 text-gray-700">
                    <li className="flex items-start gap-2"><span className="text-blue-600 font-bold">•</span>{selectedLanguage === 'hindi' ? 'जिला कानूनी सेवा प्राधिकरण (DLSA) से संपर्क करें' : 'Contact District Legal Services Authority (DLSA)'}</li>
                    <li className="flex items-start gap-2"><span className="text-blue-600 font-bold">•</span>{selectedLanguage === 'hindi' ? 'राज्य कानूनी सेवा प्राधिकरण (SLSA) कार्यालय' : 'State Legal Services Authority (SLSA) offices'}</li>
                    <li className="flex items-start gap-2"><span className="text-blue-600 font-bold">•</span>{selectedLanguage === 'hindi' ? 'राष्ट्रीय कानूनी सेवा प्राधिकरण: nalsa.gov.in' : 'National Legal Services Authority: nalsa.gov.in'}</li>
                  </ul>
                </div>
                <div className="p-6 bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl border-2 border-green-200">
                  <h3 className="text-xl font-bold text-gray-900 mb-3">{selectedLanguage === 'hindi' ? '⚖️ लोक अदालत' : '⚖️ Lok Adalat'}</h3>
                  <ul className="space-y-2 text-gray-700">
                    <li className="flex items-start gap-2"><span className="text-green-600 font-bold">•</span>{selectedLanguage === 'hindi' ? 'कोई कोर्ट फीस नहीं' : 'No court fees'}</li>
                    <li className="flex items-start gap-2"><span className="text-green-600 font-bold">•</span>{selectedLanguage === 'hindi' ? 'तेज निपटान (आमतौर पर एक दिन में)' : 'Quick resolution (usually in one day)'}</li>
                    <li className="flex items-start gap-2"><span className="text-green-600 font-bold">•</span>{selectedLanguage === 'hindi' ? 'समझौता-आधारित समाधान' : 'Compromise-based solution'}</li>
                  </ul>
                </div>
                <div className="p-6 bg-gradient-to-br from-red-50 to-pink-50 rounded-xl border-2 border-red-200">
                  <h3 className="text-xl font-bold text-gray-900 mb-3">{selectedLanguage === 'hindi' ? '📞 महत्वपूर्ण नंबर' : '📞 Important Numbers'}</h3>
                  <div className="space-y-2 text-gray-700 font-mono">
                    <p><strong>{selectedLanguage === 'hindi' ? 'पुलिस:' : 'Police:'}</strong> 100</p>
                    <p><strong>{selectedLanguage === 'hindi' ? 'कानूनी सहायता हेल्पलाइन:' : 'Legal Aid Helpline:'}</strong> 15100</p>
                    <p><strong>{selectedLanguage === 'hindi' ? 'महिला हेल्पलाइन:' : 'Women Helpline:'}</strong> 1091</p>
                    <p><strong>{selectedLanguage === 'hindi' ? 'साइबर क्राइम:' : 'Cyber Crime:'}</strong> 1930</p>
                  </div>
                </div>
              </div>
              <div className="flex gap-4 mt-8">
                <button onClick={() => setStep(3)} className="flex-1 py-3 px-4 rounded-xl font-semibold bg-gray-200 text-gray-700 hover:bg-gray-300 transition-all">
                  {selectedLanguage === 'hindi' ? 'वापस व्याख्या पर' : 'Back to Explanation'}
                </button>
                <button
                  onClick={() => { setStep(1); setDocumentText(''); setExplanation(null); setInferenceSource(null); setApiError(null); }}
                  className="flex-1 py-3 px-4 rounded-xl font-semibold bg-gradient-to-r from-orange-600 to-red-600 text-white hover:shadow-lg transition-all"
                >
                  {selectedLanguage === 'hindi' ? 'नया दस्तावेज़ जांचें' : 'Check New Document'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Processing Overlay */}
      {isProcessing && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-8 max-w-md mx-4 text-center shadow-2xl">
            <div className="mb-6">
              <div className="w-20 h-20 mx-auto bg-gradient-to-br from-orange-600 to-red-600 rounded-full flex items-center justify-center animate-pulse">
                <Sparkles className="w-10 h-10 text-white" />
              </div>
            </div>
            <h3 className="text-2xl font-bold text-gray-900 mb-3">
              {selectedLanguage === 'hindi' ? 'AI आपके दस्तावेज़ का विश्लेषण कर रहा है' : 'AI is Analysing Your Document'}
            </h3>
            <p className="text-gray-500 text-sm mb-4">{processingStage}</p>
            <div className="mt-4 p-3 bg-emerald-50 rounded-lg border-l-4 border-emerald-600">
              <p className="text-xs text-emerald-900 font-semibold">
                <strong>🤖 {selectedLanguage === 'hindi' ? 'फाइन-ट्यून्ड Mistral-7B:' : 'Fine-tuned Mistral-7B:'}</strong>
                {' '}
                {selectedLanguage === 'hindi'
                  ? 'आपका LoRA-trained मॉडल इस दस्तावेज़ को समझ रहा है।'
                  : 'Your LoRA-trained model is processing this document.'}
              </p>
            </div>
            <div className="mt-6 flex justify-center gap-2">
              <div className="w-3 h-3 bg-orange-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
              <div className="w-3 h-3 bg-orange-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
              <div className="w-3 h-3 bg-orange-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="bg-gradient-to-r from-gray-900 to-gray-800 text-white py-8 mt-16">
        <div className="max-w-6xl mx-auto px-6 text-center">
          <p className="text-sm opacity-80 mb-2">
            {selectedLanguage === 'hindi'
              ? 'यह एक AI-संचालित शैक्षिक उपकरण है। कानूनी सलाह के लिए पेशेवर वकील से परामर्श करें।'
              : 'This is an AI-powered educational tool. For legal advice, consult a professional lawyer.'}
          </p>
          <p className="text-xs opacity-60">
            {selectedLanguage === 'hindi'
              ? 'राष्ट्रीय कानूनी सेवा प्राधिकरण (NALSA) द्वारा प्रेरित'
              : 'Inspired by National Legal Services Authority (NALSA)'}
          </p>
        </div>
      </footer>
    </div>
  );
}
