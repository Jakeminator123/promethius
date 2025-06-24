import React, { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Grid,
  Slider,
  FormControlLabel,
  Checkbox,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Alert,
  Divider,
} from '@mui/material'
import { Search as SearchIcon, Person as PersonIcon, TrendingUp as AnalysisIcon } from '@mui/icons-material'
import axios from 'axios'

function HandHistorySearch() {
  const [urlSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const playerFromUrl = urlSearchParams.get('player') || ''
  
  const [searchParams, setSearchParams] = useState({
    player: playerFromUrl,
    minPot: 0,
    maxPot: 1000,
    showdownOnly: false,
  })
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [hasSearched, setHasSearched] = useState(false)

  // Auto-search if player is provided in URL
  useEffect(() => {
    if (playerFromUrl) {
      handleSearch()
    }
  }, [playerFromUrl])

  const handleSearch = async () => {
    setLoading(true)
    setError('')
    setHasSearched(true)
    
    try {
      const response = await axios.get('/api/hand-history/search', {
        params: {
          player: searchParams.player,
          min_pot: searchParams.minPot,
          showdown_only: searchParams.showdownOnly,
        }
      })
      setResults(response.data.hands || [])
    } catch (err) {
      setError('Could not search hand histories')
      console.error('Search error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleParamChange = (param) => (event) => {
    setSearchParams({
      ...searchParams,
      [param]: event.target.value || event.target.checked
    })
  }

  const handlePotRangeChange = (event, newValue) => {
    setSearchParams({
      ...searchParams,
      minPot: newValue[0],
      maxPot: newValue[1]
    })
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Hand History Search
      </Typography>
      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        Search and filter poker hands based on various criteria
      </Typography>

      {/* Player Information Section */}
      {searchParams.player && (
        <Paper sx={{ p: 3, mt: 3, mb: 3, backgroundColor: '#f8f9fa', border: '1px solid #e0e0e0' }}>
          <Box display="flex" alignItems="center" justifyContent="space-between">
            <Box display="flex" alignItems="center" gap={2}>
              <PersonIcon color="primary" sx={{ fontSize: 32 }} />
              <Box>
                <Typography variant="h5" color="primary">
                  {searchParams.player}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Viewing hand history for this player
                </Typography>
              </Box>
            </Box>
            
            <Button
              variant="outlined"
              startIcon={<AnalysisIcon />}
              onClick={() => navigate(`/betting-analysis?player=${encodeURIComponent(searchParams.player)}`)}
              sx={{ minWidth: 200 }}
            >
              Betting Analysis
            </Button>
          </Box>
        </Paper>
      )}

      <Paper sx={{ p: 3, mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          Search Filters
        </Typography>
        
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Player"
              variant="outlined"
              value={searchParams.player}
              onChange={handleParamChange('player')}
              placeholder="Enter player name..."
            />
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Typography gutterBottom>
              Pot Size (BB): {searchParams.minPot} - {searchParams.maxPot}
            </Typography>
            <Slider
              value={[searchParams.minPot, searchParams.maxPot]}
              onChange={handlePotRangeChange}
              valueLabelDisplay="auto"
              min={0}
              max={1000}
              marks={[
                { value: 0, label: '0' },
                { value: 250, label: '250' },
                { value: 500, label: '500' },
                { value: 750, label: '750' },
                { value: 1000, label: '1000+' },
              ]}
            />
          </Grid>
          
          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={searchParams.showdownOnly}
                  onChange={handleParamChange('showdownOnly')}
                />
              }
              label="Show only hands that went to showdown"
            />
          </Grid>
          
          <Grid item xs={12}>
            <Button
              variant="contained"
              startIcon={<SearchIcon />}
              onClick={handleSearch}
              disabled={loading}
              size="large"
            >
              {loading ? 'Searching...' : 'Search'}
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mt: 3 }}>
          {error}
        </Alert>
      )}

      {loading && (
        <Box display="flex" justifyContent="center" sx={{ mt: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {/* Results Section */}
      {!loading && results.length > 0 && (
        <Box sx={{ mt: 4 }}>
          <Divider sx={{ mb: 3 }} />
          <Typography variant="h6" gutterBottom>
            Search Results ({results.length} hands found)
          </Typography>
          
          <TableContainer component={Paper} sx={{ mt: 2 }}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Hand ID</TableCell>
                  <TableCell>Player</TableCell>
                  <TableCell>Street</TableCell>
                  <TableCell>Position</TableCell>
                  <TableCell>Action</TableCell>
                  <TableCell align="right">Pot Size</TableCell>
                  <TableCell align="right">J-Score</TableCell>
                  <TableCell>Timestamp</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {results.map((hand, index) => (
                  <TableRow key={`${hand.hand_id}-${index}`} hover>
                    <TableCell>{hand.hand_id}</TableCell>
                    <TableCell>{hand.nickname || hand.player_id}</TableCell>
                    <TableCell>
                      <Chip label={hand.street} size="small" color="primary" />
                    </TableCell>
                    <TableCell>{hand.position}</TableCell>
                    <TableCell>
                      <Chip 
                        label={hand.action} 
                        size="small" 
                        color={hand.action === 'r' ? 'success' : hand.action === 'f' ? 'error' : 'default'}
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Chip label={`${hand.pot_size_bb} BB`} size="small" />
                    </TableCell>
                    <TableCell align="right">
                      <Chip 
                        label={hand.j_score} 
                        size="small"
                        color={hand.j_score > 70 ? 'success' : hand.j_score > 40 ? 'warning' : 'error'}
                      />
                    </TableCell>
                    <TableCell>
                      {new Date(hand.timestamp).toLocaleString('en-US')}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      {!loading && hasSearched && results.length === 0 && (
        <Alert severity="info" sx={{ mt: 3 }}>
          No hands found with the specified criteria
        </Alert>
      )}
    </Box>
  )
}

export default HandHistorySearch 