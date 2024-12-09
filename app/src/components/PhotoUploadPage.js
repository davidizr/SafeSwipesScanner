import React, { useState } from 'react';
import './PhotoUploadPage.css';

function PhotoUploadPage() {
  const [selectedIdImage, setSelectedIdImage] = useState(null);
  const [selectedFaceImage, setSelectedFaceImage] = useState(null);
  const [previewIdImage, setPreviewIdImage] = useState(null);
  const [previewFaceImage, setPreviewFaceImage] = useState(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [verificationResults, setVerificationResults] = useState(null);
  const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:5000';

  const handleBlacklistFromPhotos = async () => {
    const formData = new FormData();
    formData.append('idPhoto', selectedIdImage);
    if (selectedFaceImage) {
      formData.append('facePhoto', selectedFaceImage);
    }
  
    try {
      const response = await fetch(`${backendUrl}/api/blacklist-individual`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setVerificationResults({ 
          success: true,
          message: data.message
        });
      } else {
        setVerificationResults({ 
          error: data.message || 'Failed to add individual to blacklist'
        });
      }
    } catch (error) {
      console.error('Error adding to blacklist:', error);
      setVerificationResults({ 
        error: 'Error adding to blacklist'
      });
    }
  };  
  const handleImageUpload = (event, type) => {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        if (type === 'id') {
          setPreviewIdImage(e.target.result);
          setSelectedIdImage(file);
        } else {
          setPreviewFaceImage(e.target.result);
          setSelectedFaceImage(file);
        }
        setVerificationResults(null);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleVerify = async (e) => {
    e.preventDefault();
    if (!selectedIdImage) {
      setVerificationResults({ error: 'Please upload an ID photo.' });
      return;
    }

    setIsVerifying(true);
    try {
      const formData = new FormData();
      formData.append('idPhoto', selectedIdImage);
      if (selectedFaceImage) {
        formData.append('facePhoto', selectedFaceImage);
      }

      const response = await fetch(`${backendUrl}/api/upload-photo`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();

      // Set results with timeout for UI feedback
      setTimeout(() => {
        setVerificationResults({
          isValid: data.isValid,
          details: data.details || {
            name: 'N/A',
            dateOfBirth: 'N/A',
            age: 'N/A',
            expiryDate: 'N/A'
          },
          warnings: data.warnings || [],
          validationMessages: data.validationMessages || []
        });
        setIsVerifying(false);
      }, 2000);

    } catch (error) {
      console.error('Verification failed:', error);
      setVerificationResults({ error: 'Verification failed. Please try again.' });
    } finally {
      setIsVerifying(false);
    }
  };

  const handleReset = () => {
    setSelectedIdImage(null);
    setSelectedFaceImage(null);
    setPreviewIdImage(null);
    setPreviewFaceImage(null);
    setVerificationResults(null);
    setIsVerifying(false);
    // Reset the file input values
    document.getElementById('id-upload').value = '';
    document.getElementById('face-upload').value = '';
  };

  return (
    <div className="scan-main">

      <div className="scan-main">
        <header className="scan-header">
          <img src="/SafeSwipes.png" alt="SafeSwipes Logo" className="logo" />
          <p className="subtitle">Secure ID Verification System</p>
        </header>

        <div className="upload-container">
          <div className="upload-section">
            <div 
              className={`upload-box ${previewIdImage ? 'has-image' : ''}`}
              onClick={() => document.getElementById('id-upload').click()}
              style={{ cursor: 'pointer' }}
            >
              {previewIdImage ? (
                <img src={previewIdImage} alt="ID Preview" className="id-preview" />
              ) : (
                <>
                  <div className="upload-icon">📄</div>
                  <h2 className="upload-header"> Upload ID Document</h2>
                </>
              )}
            </div>
            <input
              type="file"
              accept="image/*"
              onChange={(e) => handleImageUpload(e, 'id')}
              id="id-upload"
              className="file-input"
            />
          </div>

          <div className="upload-section">
            <div 
              className={`upload-box ${previewFaceImage ? 'has-image' : ''}`}
              onClick={() => document.getElementById('face-upload').click()}
              style={{ cursor: 'pointer' }}
            >
              {previewFaceImage ? (
                <img src={previewFaceImage} alt="Face Preview" className="face-preview" />
              ) : (
                <>
                  <div className="upload-icon">👤</div>
                  <h2 className="upload-header">Upload Face Photo</h2>
                  <h3 className="optional-text">[Optional]</h3>
                </>
              )}
            </div>
            <input
              type="file"
              accept="image/*"
              onChange={(e) => handleImageUpload(e, 'face')}
              id="face-upload"
              className="file-input"
            />
          </div>
        </div>
        <div className="verification-section">
          <div className="action-buttons">
            <button 
              onClick={handleVerify} 
              className="verify-button"
              disabled={isVerifying || !selectedIdImage}
            >
              {isVerifying ? '...' : 'Verify'}
            </button>
            <button 
              onClick={handleBlacklistFromPhotos}
              className="blacklist-button"
              disabled={isVerifying || !selectedIdImage}
            >
              Blacklist
            </button>
            <button onClick={handleReset} className="reset-button">
              Reset
            </button>
          </div>
        </div>

        {verificationResults && (
          <>
            {verificationResults.error ? (
              <div className="error-message">{verificationResults.error}</div>
            ) : verificationResults.success ? (
              <div className="success-message">{verificationResults.message}</div>
            ) : (
              <>
                {verificationResults.validationMessages && verificationResults.validationMessages.map((msg, index) => (
                  <div 
                    key={index} 
                    className={`validation-warning-box ${msg.type}`}
                  >
                    {msg.type === 'underage' && '⛔ USER IS UNDER 19 YEARS OLD'}
                    {msg.type === 'blacklist' && '⛔ USER IS BLACKLISTED'}
                    {msg.type === 'expired' && '⚠️ ID IS EXPIRED'}                  
                  </div>
                ))}
                {!verificationResults.isValid && verificationResults.warnings && verificationResults.warnings.length > 0 && (
                  <div className="warnings-section">
                    <div className="warnings-grid">
                      {verificationResults.warnings.map((warning, index) => (
                        <div key={index} className="warning-item">
                          <div className="warning-header">
                            <span className="warning-code">{warning.code}</span>
                            <span className={`warning-severity ${warning.severity.toLowerCase()}`}>
                              {warning.severity}
                            </span>
                          </div>
                          <p className="warning-description">{warning.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <div className="results-grid">
                  <div className="result-item">
                    <span className="label">Valid ID:</span>
                    <span className={`value ${!verificationResults.isValid ? 'invalid' : ''}`}>
                      {verificationResults.isValid ? 'Yes' : 'No'}
                    </span>
                  </div>
                  <div className="result-item">
                    <span className="label">Name:</span>
                    <span className="value">{verificationResults.details.name}</span>
                  </div>
                  <div className="result-item">
                    <span className="label">Date of Birth:</span>
                    <span className="value">{verificationResults.details.dateOfBirth}</span>
                  </div>
                  <div className="result-item">
                    <span className="label">Age:</span>
                    <span className="value">{verificationResults.details.age}</span>
                  </div>
                </div>

                
              </>
            )}
          </>
        )}
      </div>
    </div>
  );}

export default PhotoUploadPage;