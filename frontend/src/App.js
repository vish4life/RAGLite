import './App.css';
import { useState, useRef, useEffect } from 'react';

const botImg = './bot.png';
const base_url = 'http://localhost:8001';
const headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
};
const lang_models = ['llama3.2','nemotron-3-nano','phi3:mini','nemotron-mini']


function App() {
  const [messages, setMessages] = useState('');
  const [file, setFile] = useState();
  const [chatMessages, setChatMessages] = useState([]);
  const [model, setModel] = useState('llama3.2');
  const [disableBtn, setDisableBtn] = useState(false);
  const [logger, setLogger] = useState([`${new Date().toLocaleString()} Welcome to RAG Bot!`]);
  return (
    <div className="App">
      <div className="AppHeader">
        <img style={{ width: '50px', height: '50px',filter: 'invert(100%)',marginRight: '15px' }} src={botImg} alt="" />
        <h1>RAG</h1>
      </div>
      <div className="AppBoxes">
        <Stats logger={logger}/>
        <Chat messages={messages} setMessages={setMessages} chatMessages={chatMessages} setChatMessages={setChatMessages} setLogger={setLogger} logger={logger} model={model} disableBtn={disableBtn} setDisableBtn={setDisableBtn}/>
        <div className="modelUploadBox">
          <Models model={model} setModel={setModel} setLogger={setLogger} logger={logger}/>
          <Upload model={model} setLogger={setLogger} file={file} setFile={setFile} logger={logger} disableBtn={disableBtn} setDisableBtn={setDisableBtn}/>
        </div>
      </div>
      <div className="footer">
        <p>Lakshmi Shashank Chodavarapu © 2025 RAG &#9679; Bot</p>
      </div>
    </div>
  );
};

const Chat = ({messages, setMessages, chatMessages, setChatMessages,setLogger,logger,model,disableBtn,setDisableBtn}) => {
  const handleSend = async () => {
    setDisableBtn(true);
    setChatMessages([...chatMessages, {role: 'user', content: messages}]);
    setMessages('');
    setLogger(prev => [...prev, `${new Date().toLocaleString()} user: ${messages}`]);
    
    try {
      const response = await fetch(`${base_url}/ragengine/chats/query/`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({
          query: messages,
          // document_id: ... (optional)
        }),
      });
      // const response = await fetch(`${base_url}/ragengine/chats/testinput/`, {
      //   method: 'POST',
      //   headers: headers,
      //   body: JSON.stringify({
      //     query: messages,
      //     model: model,
      //     // document_id: ... (optional)
      //   }),
      // });
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();
      console.log(data);
      
      // The backend returns 'answer', not 'response'
      const botAnswer = data.answer || "No answer received.";
      
      setChatMessages(prev => [...prev, {role: 'bot', content: botAnswer}]);
      setLogger(prev => [...prev, `${new Date().toLocaleString()} bot response received`]);
    } catch (error) {
      console.error('Fetch error:', error);
      setLogger(prev => [...prev, `${new Date().toLocaleString()} error: ${error.message}`]);
      setChatMessages(prev => [...prev, {role: 'bot', content: "Sorry, I encountered an error connecting to the server."}]);
    } finally {
      setDisableBtn(false);
    }
};
const chatRefEnd = useRef(null);
useEffect(() => {
    chatRefEnd.current?.scrollIntoView({ behavior: 'smooth' });
}, [chatMessages]);
  return (
    <div className="chatbox">
      <p className="boxheader">Chat</p>
      <div className='chat-container'>
        <div className='chatbox-content'>
          {chatMessages.map((message, index) => (
            <p key={index} className={message.role === 'user' ? 'user-message' : 'bot-message'}>{message.content}</p>
          ))}
          <div ref={chatRefEnd} />
        </div>
        <div className='chatbox-input'>
          <textarea placeholder="Type your message..." value = {messages} onChange={(e) => setMessages(e.target.value)}/>
          <button onClick={() => {handleSend()}} disabled={disableBtn}>&#9775;</button>
        </div>
      </div>
      
    </div>
  );
};
const Upload = ({model, setLogger, logger, file, setFile, disableBtn, setDisableBtn}) => {
  const handleUpload = async () => {
    if (!file) {
      setLogger(prev => [...prev, `${new Date().toLocaleString()} error: No file selected`]);
      return;
    }

    setLogger(prev => [...prev, `${new Date().toLocaleString()} ${file.name} sent for uploading`]);
    
    const formData = new FormData();
    formData.append('file', file);
    setDisableBtn(true);
    try {
      const response = await fetch(`${base_url}/ragengine/documents/upload/`, {
        method: 'POST',
        // Note: Do NOT set Content-Type header when sending FormData
        // The browser will automatically set it to multipart/form-data with the correct boundary
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Server error: ${response.status}`);
      }

      const data = await response.json();
      console.log(data.message);
      if(data.message === 'Document already exists'){
        setLogger(prev => [...prev, `${new Date().toLocaleString()} ${file.name} already exists`]);
      }else{
        setLogger(prev => [...prev, `${new Date().toLocaleString()} ${file.name} uploaded successfully`]);
      }
      setFile(null);
      setDisableBtn(false);      
      // Clear the file input
      const fileInput = document.querySelector('input[type="file"]');
      if (fileInput) fileInput.value = '';
      
    } catch (error) {
      console.error('Upload error:', error);
      setLogger(prev => [...prev, `${new Date().toLocaleString()} error: ${error.message}`]);
    }
  }
  return (
    <div className="uploadbox">
      <p className="boxheader">Upload PDF file</p>
      <div className="uploadbox-content">
        <input type="file" accept=".pdf" onChange={(e) => setFile(e.target.files[0])}/>
        <button onClick={() => {handleUpload()}} disabled={disableBtn}>&#8682;</button>
      </div>
    </div>
  );
};

const Stats = ({logger}) => {
  const logEndRef = useRef(null);

  // Auto-scroll to bottom when new logs are added
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logger]);

  return (
    <div className="statsbox">
      <p className="boxheader">Logger</p>
      <div className="statsbox-content">
        {logger.map((lg, index) => (
          <p key={index}>{lg}</p>
        ))}
        {/* Invisible element at the end to scroll to */}
        <div ref={logEndRef} />
      </div>
    </div>
  );
};

const Models = ({model, setModel, setLogger, logger}) => {
  return (
    <div className="modelsbox">
      <p className="boxheader">Models</p>
      {lang_models.map((mdl,index) => (
        <div key={index} className='modelbuttonbox'>
          <button className={model === mdl ? 'modelbuttonactive' : 'modelbutton'} onClick={() => {
            setModel(mdl);
            setLogger([...logger, `${new Date().toLocaleString()} Selected model: ${mdl}`]); 
          }}>{mdl}</button>
        </div>
      ))}
    </div>
  );
};

export default App;
