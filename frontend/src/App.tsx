import { Route, Routes } from 'react-router-dom'
import { ResultsPage } from './pages/ResultsPage'
import { TripInputPage } from './pages/TripInputPage'

export function App() {
  return (
    <Routes>
      <Route path="/" element={<TripInputPage />} />
      <Route path="/results" element={<ResultsPage />} />
    </Routes>
  )
}
