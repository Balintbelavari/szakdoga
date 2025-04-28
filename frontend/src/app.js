import React, { useState } from "react";
import "./app.css";
import logo from "./assets/bb_logo_w.png";

function App() {
  const [message, setMessage] = useState("");
  const [lastCheckedMessage, setLastCheckedMessage] = useState("");
  const [cleanedMessage, setCleanedMessage] = useState("");
  const [prediction, setPrediction] = useState("");
  const [confidence, setConfidence] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handlePredict = async (inputMessage) => {
    const text = inputMessage || message; // Use the provided example or typed input

    if (!text.trim()) {
      setError("Error: Message cannot be empty");
      return;
    }

    try {
      setError("");
      setPrediction("");
      setCleanedMessage("");
      setConfidence(null);
      setLastCheckedMessage(text); // Store the checked message
      setLoading(true);
      setMessage(text); // Update textarea for example buttons
      const response = await fetch(
        "https://szakdolgozat-nh9z.onrender.com/predict",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          `Failed to fetch prediction: ${
            errorData.detail || response.statusText
          }`
        );
      }

      const data = await response.json();
      setPrediction(data.prediction);
      setCleanedMessage(data.cleaned_message);
      setConfidence(data.confidence);
    } catch (err) {
      setError("Error: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <div className="header">
        <img src={logo} alt="Logo" className="logo" />
      </div>
      <h1>
        Is it a <span className="highlight">scam</span>?
      </h1>
      <div className="input-container">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Type something here..."
          rows="1"
          style={{
            height: "32px",
            minHeight: "20px",
            maxHeight: "160px",
            overflowY: "auto",
          }}
          onInput={(e) => {
            e.target.style.height = "20px";
            if (e.target.scrollHeight > 20) {
              e.target.style.height =
                Math.min(e.target.scrollHeight, 160) + "px";
            }
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handlePredict();
            }
          }}
        />
        <button onClick={() => handlePredict()} disabled={loading}>
          Check
        </button>
      </div>
      {loading && <p>Loading...</p>}
      {prediction && (
        <div className="results">
          <table>
            <tr>
              <td className="prediction-label">Prediction:</td>
              <td className="prediction">
                {prediction === "spam" ? "Harmful 🚨" : "Safe ✅"}
              </td>
            </tr>
            <tr>
              <td className="prediction-label">Confidence: </td>
              <td className="prediction">
                {confidence ? `${(confidence * 100).toFixed(2)}%` : "N/A"}
              </td>
            </tr>
          </table>
        </div>
      )}
      {error && <p className="error">{error}</p>}

      {/* Example Messages Section */}
      <div className="example-container">
        <p className="example-title">Try these:</p>
        <div className="example-buttons">
          <button
            className="example-button"
            onClick={() => handlePredict("Do you want to have lunch tomorrow?")}
          >
            Do you want to have lunch tomorrow?
          </button>
          <button
            className="example-button"
            onClick={() => handlePredict("Your membership expires in 10 days.")}
          >
            Your membership expires in 10 days.
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
