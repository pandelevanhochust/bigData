import { useState } from 'react'
import './App.css'
import FraudDetectionDashboard from "./FraudDetectionDashboard.jsx";

function App() {
  const [count, setCount] = useState(0)

  return (
    <>
      {/*<FraudDetectionDashboard/>*/}
        <TransactionDashboard/>
    </>
  )
}

export default App
