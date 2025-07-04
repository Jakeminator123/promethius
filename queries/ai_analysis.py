"""
AI Analysis module for poker player evaluation using OpenAI GPT-4o
"""
import os
import json
from typing import Dict, List, Optional, Any
import openai
from openai import OpenAI
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = None
try:
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key and api_key.startswith('sk-'):
        client = OpenAI(api_key=api_key)
        logger.info("OpenAI client initialized successfully")
    else:
        logger.warning("OPENAI_API_KEY not found or invalid in environment variables")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {e}")


def analyze_player(player_stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze a single player using GPT-4o
    
    Args:
        player_stats: Dictionary containing player statistics
        
    Returns:
        Dictionary with AI analysis results
    """
    if not client:
        return {
            "error": "AI service not available. Please check API key configuration.",
            "status": "error"
        }
    
    try:
        # Ensure we have valid stats
        if not isinstance(player_stats, dict):
            return {
                "error": "Invalid player data format",
                "status": "error"
            }
        
        # Prepare the prompt with player stats
        prompt = f"""
        Analyze this poker player's statistics and provide insights about their playing style, potential weaknesses, and fraud risk assessment.
        
        Player Statistics:
        - Nickname: {player_stats.get('nickname', 'Unknown')}
        - Total Hands: {player_stats.get('total_hands', 0)}
        - Win Rate: {player_stats.get('winrate_bb100', 0):.2f} BB/100
        - VPIP: {player_stats.get('vpip', 0):.1f}%
        - PFR: {player_stats.get('pfr', 0):.1f}%
        - Average J-Score: {player_stats.get('avg_j_score', 0):.1f}
        - Preflop Score: {player_stats.get('avg_preflop_score', 0):.1f}
        - Postflop Score: {player_stats.get('avg_postflop_score', 0):.1f}
        
        Please provide:
        1. Playing style assessment (tight/loose, aggressive/passive)
        2. Key strengths and weaknesses
        3. Fraud risk assessment (0-100 scale)
        4. Recommendations for playing against this opponent
        5. Any unusual patterns or red flags
        
        Format your response as JSON with keys: 
        playing_style, strengths, weaknesses, fraud_risk, recommendations, red_flags
        
        Keep all values as strings except fraud_risk which should be a number.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using 4o-mini for cost efficiency
            messages=[
                {"role": "system", "content": "You are a poker analytics expert specializing in player behavior analysis and fraud detection."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=500
        )
        
        # Parse the response
        content = response.choices[0].message.content
        if not content:
            return {
                "error": "Empty response from AI",
                "status": "error"
            }
        analysis = json.loads(content)
        
        # Ensure all expected fields are strings (except fraud_risk)
        for key in ['playing_style', 'strengths', 'weaknesses', 'recommendations', 'red_flags']:
            if key in analysis and not isinstance(analysis[key], str):
                analysis[key] = str(analysis[key])
        
        # Ensure fraud_risk is a number
        if 'fraud_risk' in analysis:
            try:
                analysis['fraud_risk'] = float(analysis['fraud_risk'])
            except:
                analysis['fraud_risk'] = 50  # Default if conversion fails
        
        return {
            "status": "success",
            "analysis": analysis,
            "player_name": player_stats.get('nickname', player_stats.get('player_id', 'Unknown')),
            "total_hands": player_stats.get('total_hands', 0)
        }
        
    except Exception as e:
        logger.error(f"AI analysis failed: {e}")
        return {
            "error": f"Analysis failed: {str(e)}",
            "status": "error"
        }


def analyze_multiple_players(players_stats: List[Dict[str, Any]], max_players: int = 5) -> Dict[str, Any]:
    """
    Analyze multiple players and provide comparative insights
    
    Args:
        players_stats: List of player statistics dictionaries
        max_players: Maximum number of players to analyze (default 5)
        
    Returns:
        Dictionary with comparative analysis
    """
    if not client:
        return {
            "error": "AI service not available. Please check API key configuration.",
            "status": "error"
        }
    
    # Analyze ALL players (up to 25) instead of limiting
    players_to_analyze = players_stats[:25]  # Take up to 25 players
    
    try:
        # Prepare comprehensive player summaries with all available stats
        player_summaries = []
        for i, p in enumerate(players_to_analyze):
            summary = f"""
            Player {i+1}: {p.get('nickname', 'Unknown')}
            - Total Hands: {p.get('total_hands', 0)}
            - Win Rate: {p.get('winrate_bb100', 0):.2f} BB/100
            - VPIP: {p.get('vpip', 0):.1f}%
            - PFR: {p.get('pfr', 0):.1f}%
            - J-Score: {p.get('avg_j_score', 0):.1f}
            - Preflop Score: {p.get('avg_preflop_score', 0):.1f}
            - Postflop Score: {p.get('avg_postflop_score', 0):.1f}
            """
            player_summaries.append(summary.strip())
        
        prompt = f"""
        Analyze these {len(players_to_analyze)} poker players from the dashboard and identify what stands out.
        Focus on finding anomalies, unusual patterns, and potential bot/fraud indicators.
        
        Players data:
        {chr(10).join(player_summaries)}
        
        Please analyze and provide:
        1. **Anomaly Detection**: Which players show unusual statistical patterns that deviate significantly from normal play?
        2. **Bot Indicators**: Identify players with stats that suggest automated/bot play (too perfect, unnatural combinations)
        3. **Statistical Outliers**: Players whose stats are extreme in any dimension
        4. **Suspicious Patterns**: Any groups of players with suspiciously similar stats (potential bot farm)
        5. **Risk Assessment**: Rank the top 5 most suspicious players with specific reasons
        
        Focus on patterns that would be hard for a human to spot by just looking at the numbers.
        
        Format your response as JSON with keys:
        anomalies, bot_indicators, outliers, suspicious_patterns, top_suspicious_players
        
        Keep all values as detailed strings explaining what stands out.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert poker analyst specializing in fraud detection and statistical anomaly identification. You excel at finding patterns in data that humans might miss."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=1000  # Increased for more detailed analysis
        )
        
        content = response.choices[0].message.content
        if not content:
            return {
                "error": "Empty response from AI",
                "status": "error"
            }
        analysis = json.loads(content)
        
        # Ensure all fields are strings
        for key in analysis:
            if not isinstance(analysis[key], str):
                analysis[key] = str(analysis[key])
        
        return {
            "status": "success",
            "analysis": analysis,
            "players_analyzed": len(players_to_analyze),
            "total_players": len(players_stats)
        }
        
    except Exception as e:
        logger.error(f"Multi-player analysis failed: {e}")
        return {
            "error": f"Analysis failed: {str(e)}",
            "status": "error"
        }


def get_ai_status() -> Dict[str, Any]:
    """Check if AI service is available"""
    return {
        "available": client is not None,
        "model": "gpt-4o-mini" if client else None,
        "status": "ready" if client else "not_configured"
    } 