import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  Grid,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Collapse,
  IconButton,
  Divider,
  Stack
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Person as PersonIcon
} from '@mui/icons-material';

const HandHistoryViewer = ({ handId, onClose }) => {
  const [handData, setHandData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedStreets, setExpandedStreets] = useState({
    preflop: true,
    flop: false,
    turn: false,
    river: false
  });

  useEffect(() => {
    if (handId) {
      fetchHandDetails();
    }
  }, [handId]);

  const fetchHandDetails = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/hand-detailed-view?hand_id=${handId}`);
      const result = await response.json();
      
      if (result.success) {
        setHandData(result.data);
      } else {
        setError(result.error || 'Failed to load hand details');
      }
    } catch (err) {
      setError('Error fetching hand details');
      console.error('Hand details error:', err);
    } finally {
      setLoading(false);
    }
  };

  const toggleStreet = (street) => {
    setExpandedStreets(prev => ({
      ...prev,
      [street]: !prev[street]
    }));
  };

  const formatAction = (action) => {
    const actionMap = {
      'f': 'Fold',
      'c': 'Call',
      'r': 'Raise',
      'x': 'Check'
    };
    return actionMap[action] || action;
  };

  const formatBetSize = (amount, pot, bigBlind) => {
    if (!amount || amount === 0) return '';
    const bbSize = Math.round(amount / bigBlind * 10) / 10;
    const potFrac = pot > 0 ? Math.round((amount / pot) * 100) : 0;
    return `${bbSize}bb (${potFrac}% pot)`;
  };

  const getStreetActions = (street) => {
    if (!handData?.actions) return [];
    return handData.actions.filter(action => action.street === street);
  };

  const renderActionRow = (action, index) => (
    <TableRow key={index} sx={{ backgroundColor: index % 2 === 0 ? 'background.default' : 'background.paper' }}>
      <TableCell>{action.position}</TableCell>
      <TableCell>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <PersonIcon fontSize="small" />
          {action.nickname}
        </Box>
      </TableCell>
      <TableCell>
        <Chip 
          label={formatAction(action.action)} 
          size="small" 
          color={action.action === 'r' ? 'primary' : action.action === 'f' ? 'error' : 'default'}
        />
      </TableCell>
      <TableCell>
        {action.amount_to && action.amount_to > 0 ? 
          formatBetSize(action.amount_to, action.pot_before, handData.hand_info.big_blind) : 
          '-'
        }
      </TableCell>
      <TableCell>{action.j_score ? `${action.j_score}/100` : '-'}</TableCell>
      <TableCell>
        <Typography variant="caption" color="text.secondary">
          {action.intention || '-'}
        </Typography>
      </TableCell>
    </TableRow>
  );

  const renderStreetSection = (street) => {
    const actions = getStreetActions(street);
    if (actions.length === 0) return null;

    const isExpanded = expandedStreets[street];
    const board = handData.street_boards[street];

    return (
      <Card key={street} sx={{ mb: 2 }}>
        <CardContent sx={{ pb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Typography variant="h6" sx={{ textTransform: 'capitalize' }}>
                {street}
              </Typography>
              {board && (
                <Box sx={{ display: 'flex', gap: 0.5 }}>
                  {board.split(',').map((card, idx) => (
                    <Chip key={idx} label={card} size="small" variant="outlined" />
                  ))}
                </Box>
              )}
            </Box>
            <IconButton onClick={() => toggleStreet(street)} size="small">
              {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>
          
          <Collapse in={isExpanded}>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Position</TableCell>
                    <TableCell>Player</TableCell>
                    <TableCell>Action</TableCell>
                    <TableCell>Size</TableCell>
                    <TableCell>J-Score</TableCell>
                    <TableCell>Intention</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {actions.map((action, idx) => renderActionRow(action, idx))}
                </TableBody>
              </Table>
            </TableContainer>
          </Collapse>
        </CardContent>
      </Card>
    );
  };

  if (loading) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography>Loading hand details...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="error">{error}</Typography>
      </Box>
    );
  }

  if (!handData) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography>No hand data available</Typography>
      </Box>
    );
  }

  const { hand_info, players } = handData;

  return (
    <Paper sx={{ p: 2, maxHeight: '80vh', overflow: 'auto' }}>
      {/* Hand Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h5" gutterBottom>
          Hand {hand_info.hand_id}
        </Typography>
        
        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={12} md={6}>
            <Stack direction="row" spacing={2}>
              <Chip label={`${hand_info.small_blind}/${hand_info.big_blind}${hand_info.ante ? `/${hand_info.ante}` : ''}`} variant="outlined" />
              <Chip label={hand_info.pot_type} color="primary" variant="outlined" />
              <Chip label={`${hand_info.players_cnt} players`} variant="outlined" />
            </Stack>
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="body2" color="text.secondary">
              Date: {hand_info.hand_date}
            </Typography>
          </Grid>
        </Grid>

        {/* Players */}
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle1" gutterBottom>Players</Typography>
          <Grid container spacing={1}>
            {players.map((player, idx) => (
              <Grid item key={idx}>
                <Card variant="outlined" sx={{ minWidth: 200 }}>
                  <CardContent sx={{ py: 1, px: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Box>
                        <Typography variant="body2" fontWeight="bold">
                          {player.position}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {player.nickname}
                        </Typography>
                      </Box>
                      <Box sx={{ textAlign: 'right' }}>
                        <Typography variant="body2">
                          {player.holecards || 'Unknown'}
                        </Typography>
                        <Typography variant="caption" color={player.money_won >= 0 ? 'success.main' : 'error.main'}>
                          {player.money_won >= 0 ? '+' : ''}{player.money_won}bb
                        </Typography>
                      </Box>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>
      </Box>

      <Divider sx={{ mb: 2 }} />

      {/* Action History by Street */}
      <Typography variant="h6" gutterBottom>Action History</Typography>
      {['preflop', 'flop', 'turn', 'river'].map(street => renderStreetSection(street))}
    </Paper>
  );
};

export default HandHistoryViewer; 