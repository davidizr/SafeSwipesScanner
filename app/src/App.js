import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import PhotoUploadPage from './components/PhotoUploadPage';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<PhotoUploadPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;