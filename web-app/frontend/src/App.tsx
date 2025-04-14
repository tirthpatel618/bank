import React, { useEffect, useState } from 'react';
import './App.css';

interface Quote {
  id: number;
  vachanamrut_place: string;
  vachanamrut_number: string;
  quote: string;
  topic: string;
}

const App: React.FC = () => {
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);
  const [allTopics, setAllTopics] = useState<string[]>([]);
  const [showPopup, setShowPopup] = useState(false);

  useEffect(() => {
    // Fetch all quotes
    fetch('http://localhost:3001/api/quotes')
      .then((res) => res.json())
      .then((data: Quote[]) => setQuotes(data))
      .catch((err) => console.error(err));

    // Fetch all topics
    fetch('http://localhost:3001/api/topics')
      .then((res) => res.json())
      .then((data: string[]) => setAllTopics(data))
      .catch((err) => console.error(err));
  }, []);

  // Toggle selected topics
  const toggleTopic = (topic: string) => {
    if (selectedTopics.includes(topic)) {
      setSelectedTopics(selectedTopics.filter((t) => t !== topic));
    } else {
      setSelectedTopics([...selectedTopics, topic]);
    }
  };

  // Filter quotes based on selected topics
  const filteredQuotes =
    selectedTopics.length === 0
      ? quotes
      : quotes.filter((q) => selectedTopics.includes(q.topic));

  // Copy quote text to the clipboard, show popup briefly
  const copyQuoteToClipboard = (quoteText: string) => {
    navigator.clipboard.writeText(quoteText).then(() => {
      setShowPopup(true);
      setTimeout(() => {
        setShowPopup(false);
      }, 2000);
    });
  };

  return (
    <div className="app-container">
      <h1 className="heading">Vachanamrut Quotes by Topic</h1>

      <div className="topics-container">
        {allTopics.map((topic) => (
          <button
            key={topic}
            onClick={() => toggleTopic(topic)}
            className={`topic-button ${
              selectedTopics.includes(topic) ? 'active' : ''
            }`}
          >
            {topic}
          </button>
        ))}
      </div>

      <table className="quotes-table">
        <thead>
          <tr>
            <th className="table-header">Vachanamrut</th>
            <th className="table-header">Topic</th>
            <th className="table-header">Quote</th>
          </tr>
        </thead>
        <tbody>
          {filteredQuotes.map((quote) => (
            <tr key={quote.id}>
              <td className="table-cell">
                {quote.vachanamrut_place} {quote.vachanamrut_number}
              </td>
              <td className="table-cell">{quote.topic}</td>
              <td
                className="table-cell copy-cell"
                onClick={() => copyQuoteToClipboard(quote.quote)}
              >
                {quote.quote}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Show popup if state is set to true */}
      {showPopup && (
        <div className="copy-popup">
          Quote copied!
        </div>
      )}
    </div>
  );
};

export default App;
