import React, { useState, useEffect } from 'react';
import { Search, Filter, TrendingUp, Users, Target, BarChart2, Info } from 'lucide-react';

const AdvancedComparison = () => {
  const [availableFilters, setAvailableFilters] = useState({});
  const [selectedPlayer, setSelectedPlayer] = useState('');
  const [comparisonPlayer, setComparisonPlayer] = useState('');
  const [filters, setFilters] = useState({});
  const [segmentData, setSegmentData] = useState(null);
  const [segmentHands, setSegmentHands] = useState([]);
  const [distribution, setDistribution] = useState([]);
  const [loading, setLoading] = useState(false);
  const [players, setPlayers] = useState([]);
  const [expandedInfo, setExpandedInfo] = useState(false);

  // Load available filters on mount
  useEffect(() => {
    fetchAvailableFilters();
    fetchPlayers();
  }, []);

  const fetchAvailableFilters = async () => {
    try {
      const response = await fetch('/api/advanced-comparison/filters');
      const data = await response.json();
      if (data.success) {
        setAvailableFilters(data.filters);
      }
    } catch (error) {
      console.error('Error fetching filters:', error);
    }
  };

  const fetchPlayers = async () => {
    try {
      const response = await fetch('/api/players?limit=200');
      const data = await response.json();
      setPlayers(data.players || []);
    } catch (error) {
      console.error('Error fetching players:', error);
    }
  };

  const fetchSegmentData = async () => {
    if (!selectedPlayer) return;

    setLoading(true);
    try {
      // Build query params
      const params = new URLSearchParams({ player_id: selectedPlayer });
      if (comparisonPlayer) params.append('comparison_player_id', comparisonPlayer);
      
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== '' && value !== null && value !== undefined) {
          params.append(key, value);
        }
      });

      // Fetch segment data
      const segmentResponse = await fetch(`/api/advanced-comparison/segment?${params}`);
      const segmentResult = await segmentResponse.json();
      if (segmentResult.success) {
        setSegmentData(segmentResult.data);
      }

      // Fetch hands matching segment
      const handsResponse = await fetch(`/api/advanced-comparison/hands?${params}&limit=10`);
      const handsResult = await handsResponse.json();
      if (handsResult.success) {
        setSegmentHands(handsResult.hands);
      }

      // Fetch distribution
      const distParams = new URLSearchParams(params);
      distParams.delete('player_id');
      distParams.delete('comparison_player_id');
      distParams.append('group_by', 'player_id');
      
      const distResponse = await fetch(`/api/advanced-comparison/distribution?${distParams}`);
      const distResult = await distResponse.json();
      if (distResult.success) {
        setDistribution(distResult.distribution);
      }
    } catch (error) {
      console.error('Error fetching segment data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (filterName, value) => {
    setFilters(prev => ({
      ...prev,
      [filterName]: value === '' ? undefined : value
    }));
  };

  const formatNumber = (num) => {
    if (num === null || num === undefined) return '-';
    return Number(num).toFixed(1);
  };

  const formatPercent = (num) => {
    if (num === null || num === undefined) return '-';
    return `${Number(num).toFixed(1)}%`;
  };

  const getActiveFiltersCount = () => {
    return Object.values(filters).filter(v => v !== '' && v !== null && v !== undefined).length;
  };

  const clearFilters = () => {
    setFilters({});
  };

  return (
    <div className="max-w-7xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Advanced Player Comparison</h1>

      {/* Player Selection */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4 flex items-center">
          <Users className="mr-2" />
          Player Selection
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Main Player *
            </label>
            <select
              value={selectedPlayer}
              onChange={(e) => setSelectedPlayer(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select a player...</option>
              {players.map(player => (
                <option key={player.player_id} value={player.player_id}>
                  {player.nickname || player.player_id} ({player.hands_played} hands)
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Compare With (Optional)
            </label>
            <select
              value={comparisonPlayer}
              onChange={(e) => setComparisonPlayer(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">No comparison...</option>
              {players.filter(p => p.player_id !== selectedPlayer).map(player => (
                <option key={player.player_id} value={player.player_id}>
                  {player.nickname || player.player_id} ({player.hands_played} hands)
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold flex items-center">
            <Filter className="mr-2" />
            Segment Filters
            {getActiveFiltersCount() > 0 && (
              <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded-full">
                {getActiveFiltersCount()} active
              </span>
            )}
          </h2>
          {getActiveFiltersCount() > 0 && (
            <button
              onClick={clearFilters}
              className="text-sm text-red-600 hover:text-red-800"
            >
              Clear all filters
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Street Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Street</label>
            <select
              value={filters.street || ''}
              onChange={(e) => handleFilterChange('street', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="">All streets</option>
              {availableFilters.streets?.map(street => (
                <option key={street} value={street}>{street}</option>
              ))}
            </select>
          </div>

          {/* Position Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Position</label>
            <select
              value={filters.position || ''}
              onChange={(e) => handleFilterChange('position', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="">All positions</option>
              {availableFilters.positions?.map(pos => (
                <option key={pos} value={pos}>{pos}</option>
              ))}
            </select>
          </div>

          {/* Action Label Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Action</label>
            <select
              value={filters.action_label || ''}
              onChange={(e) => handleFilterChange('action_label', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="">All actions</option>
              {availableFilters.action_labels?.map(action => (
                <option key={action} value={action}>{action}</option>
              ))}
            </select>
          </div>

          {/* J-Score Range */}
          <div className="col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">J-Score Range</label>
            <div className="flex gap-2">
              <input
                type="number"
                placeholder="Min"
                value={filters.min_j_score || ''}
                onChange={(e) => handleFilterChange('min_j_score', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                min="0"
                max="100"
              />
              <span className="py-2">-</span>
              <input
                type="number"
                placeholder="Max"
                value={filters.max_j_score || ''}
                onChange={(e) => handleFilterChange('max_j_score', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                min="0"
                max="100"
              />
            </div>
          </div>

          {/* Pot Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Pot Type</label>
            <select
              value={filters.pot_type || ''}
              onChange={(e) => handleFilterChange('pot_type', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="">All pot types</option>
              {availableFilters.pot_types?.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>

          {/* More filters in expandable section */}
          {expandedInfo && (
            <>
              {/* Preflop Score Range */}
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Preflop Score Range</label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    placeholder="Min"
                    value={filters.min_preflop_score || ''}
                    onChange={(e) => handleFilterChange('min_preflop_score', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                    min="0"
                    max="100"
                  />
                  <span className="py-2">-</span>
                  <input
                    type="number"
                    placeholder="Max"
                    value={filters.max_preflop_score || ''}
                    onChange={(e) => handleFilterChange('max_preflop_score', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                    min="0"
                    max="100"
                  />
                </div>
              </div>

              {/* Postflop Score Range */}
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Postflop Score Range</label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    placeholder="Min"
                    value={filters.min_postflop_score || ''}
                    onChange={(e) => handleFilterChange('min_postflop_score', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                    min="0"
                    max="100"
                  />
                  <span className="py-2">-</span>
                  <input
                    type="number"
                    placeholder="Max"
                    value={filters.max_postflop_score || ''}
                    onChange={(e) => handleFilterChange('max_postflop_score', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                    min="0"
                    max="100"
                  />
                </div>
              </div>

              {/* Size Category */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Bet Size Category</label>
                <select
                  value={filters.size_cat || ''}
                  onChange={(e) => handleFilterChange('size_cat', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                >
                  <option value="">All sizes</option>
                  {availableFilters.size_categories?.map(size => (
                    <option key={size} value={size}>{size}</option>
                  ))}
                </select>
              </div>

              {/* IP Status */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">IP Status</label>
                <select
                  value={filters.ip_status || ''}
                  onChange={(e) => handleFilterChange('ip_status', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                >
                  <option value="">All</option>
                  {availableFilters.ip_status?.map(status => (
                    <option key={status} value={status}>{status}</option>
                  ))}
                </select>
              </div>

              {/* Intention */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Intention</label>
                <select
                  value={filters.intention || ''}
                  onChange={(e) => handleFilterChange('intention', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                >
                  <option value="">All intentions</option>
                  {availableFilters.intentions?.map(intention => (
                    <option key={intention} value={intention}>{intention}</option>
                  ))}
                </select>
              </div>

              {/* Players Left */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Players Left</label>
                <input
                  type="number"
                  value={filters.players_left || ''}
                  onChange={(e) => handleFilterChange('players_left', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  min="2"
                  max="9"
                  placeholder="Any"
                />
              </div>
            </>
          )}
        </div>

        <div className="mt-4 flex justify-between items-center">
          <button
            onClick={() => setExpandedInfo(!expandedInfo)}
            className="text-sm text-blue-600 hover:text-blue-800 flex items-center"
          >
            <Info className="w-4 h-4 mr-1" />
            {expandedInfo ? 'Show fewer filters' : 'Show more filters'}
          </button>
          
          <button
            onClick={fetchSegmentData}
            disabled={!selectedPlayer || loading}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 flex items-center"
          >
            {loading ? (
              <span>Loading...</span>
            ) : (
              <>
                <Search className="w-4 h-4 mr-2" />
                Analyze Segment
              </>
            )}
          </button>
        </div>
      </div>

      {/* Results */}
      {segmentData && (
        <>
          {/* Comparison Stats */}
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center">
              <BarChart2 className="mr-2" />
              Segment Analysis
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Player Stats */}
              <div className="border rounded-lg p-4">
                <h3 className="font-semibold mb-3 text-blue-600">
                  {selectedPlayer} (Selected Player)
                </h3>
                {segmentData.player_stats.action_count > 0 ? (
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>Actions:</span>
                      <span className="font-medium">{segmentData.player_stats.action_count}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Hands:</span>
                      <span className="font-medium">{segmentData.player_stats.hand_count}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Avg J-Score:</span>
                      <span className="font-medium">{formatNumber(segmentData.player_stats.avg_j_score)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Win Rate:</span>
                      <span className="font-medium">{formatPercent(segmentData.player_stats.win_rate)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Avg Raise Size:</span>
                      <span className="font-medium">{formatNumber(segmentData.player_stats.avg_raise_size)}</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-gray-500 text-sm">No data for this segment</p>
                )}
              </div>

              {/* Population Average */}
              <div className="border rounded-lg p-4">
                <h3 className="font-semibold mb-3 text-green-600">
                  Population Average
                </h3>
                {segmentData.population_stats.total_actions > 0 ? (
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>Total Actions:</span>
                      <span className="font-medium">{segmentData.population_stats.total_actions}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Unique Players:</span>
                      <span className="font-medium">{segmentData.population_stats.unique_players}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Avg J-Score:</span>
                      <span className="font-medium">{formatNumber(segmentData.population_stats.avg_j_score)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Avg Win Rate:</span>
                      <span className="font-medium">{formatPercent(segmentData.population_stats.avg_win_rate)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Avg Raise Size:</span>
                      <span className="font-medium">{formatNumber(segmentData.population_stats.avg_raise_size)}</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-gray-500 text-sm">No population data for this segment</p>
                )}
              </div>

              {/* Comparison Player */}
              {comparisonPlayer && (
                <div className="border rounded-lg p-4">
                  <h3 className="font-semibold mb-3 text-purple-600">
                    {comparisonPlayer} (Comparison)
                  </h3>
                  {segmentData.comparison_stats?.action_count > 0 ? (
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span>Actions:</span>
                        <span className="font-medium">{segmentData.comparison_stats.action_count}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Hands:</span>
                        <span className="font-medium">{segmentData.comparison_stats.hand_count}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Avg J-Score:</span>
                        <span className="font-medium">{formatNumber(segmentData.comparison_stats.avg_j_score)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Win Rate:</span>
                        <span className="font-medium">{formatPercent(segmentData.comparison_stats.win_rate)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Avg Raise Size:</span>
                        <span className="font-medium">{formatNumber(segmentData.comparison_stats.avg_raise_size)}</span>
                      </div>
                    </div>
                  ) : (
                    <p className="text-gray-500 text-sm">No data for this segment</p>
                  )}
                </div>
              )}
            </div>

            {/* Performance vs Average */}
            {segmentData.player_stats.action_count > 0 && segmentData.population_stats.avg_j_score > 0 && (
              <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                <h4 className="font-semibold mb-2">Performance Analysis</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">J-Score vs Population:</span>
                    <span className={`ml-2 font-medium ${
                      segmentData.player_stats.avg_j_score > segmentData.population_stats.avg_j_score
                        ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {segmentData.player_stats.avg_j_score > segmentData.population_stats.avg_j_score ? '+' : ''}
                      {formatNumber(segmentData.player_stats.avg_j_score - segmentData.population_stats.avg_j_score)}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600">Win Rate vs Population:</span>
                    <span className={`ml-2 font-medium ${
                      segmentData.player_stats.win_rate > segmentData.population_stats.avg_win_rate
                        ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {segmentData.player_stats.win_rate > segmentData.population_stats.avg_win_rate ? '+' : ''}
                      {formatNumber(segmentData.player_stats.win_rate - segmentData.population_stats.avg_win_rate)}%
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Top Players in Segment */}
          {distribution.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6 mb-6">
              <h2 className="text-xl font-semibold mb-4">Top Players in This Segment</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-2">Player</th>
                      <th className="text-right py-2">Actions</th>
                      <th className="text-right py-2">Hands</th>
                      <th className="text-right py-2">Avg J-Score</th>
                      <th className="text-right py-2">Win Rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {distribution.slice(0, 10).map((item, idx) => (
                      <tr key={idx} className="border-b hover:bg-gray-50">
                        <td className="py-2">{item.nickname || item.player_id}</td>
                        <td className="text-right">{item.action_count}</td>
                        <td className="text-right">{item.hand_count}</td>
                        <td className="text-right">{formatNumber(item.avg_j_score)}</td>
                        <td className="text-right">{formatPercent(item.win_rate)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Sample Hands */}
          {segmentHands.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">Sample Hands from Segment</h2>
              <div className="space-y-4">
                {segmentHands.map((hand, idx) => (
                  <div key={idx} className="border rounded-lg p-4 hover:bg-gray-50">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <span className="font-medium">{hand.hand_id}</span>
                        <span className="ml-2 text-sm text-gray-500">{hand.hand_date}</span>
                      </div>
                      <div className="text-sm">
                        <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded">
                          {hand.position}
                        </span>
                        <span className="ml-2 px-2 py-1 bg-green-100 text-green-800 rounded">
                          {hand.street}
                        </span>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                      <div>
                        <span className="text-gray-600">Action:</span>
                        <span className="ml-1 font-medium">{hand.action_label}</span>
                      </div>
                      <div>
                        <span className="text-gray-600">J-Score:</span>
                        <span className="ml-1 font-medium">{formatNumber(hand.j_score)}</span>
                      </div>
                      <div>
                        <span className="text-gray-600">Size:</span>
                        <span className="ml-1 font-medium">{formatNumber(hand.size_frac)}</span>
                      </div>
                      <div>
                        <span className="text-gray-600">Won:</span>
                        <span className={`ml-1 font-medium ${hand.money_won > 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {hand.money_won > 0 ? '+' : ''}{formatNumber(hand.money_won)}
                        </span>
                      </div>
                    </div>
                    {hand.holecards && (
                      <div className="mt-2 text-sm">
                        <span className="text-gray-600">Cards:</span>
                        <span className="ml-1 font-mono">{hand.holecards}</span>
                        {hand.board_cards && (
                          <>
                            <span className="mx-2">|</span>
                            <span className="font-mono">{hand.board_cards}</span>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default AdvancedComparison; 