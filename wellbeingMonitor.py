from textblob import TextBlob
from typing import List, Dict, Any
import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

sentiment_analyzer = SentimentIntensityAnalyzer()

wellbeing_flags = []
class WellbeingMonitor:
    def __init__(self):
        self.stress_keywords = [
            'overwhelmed', 'stressed', 'can\'t handle', 'too much', 'giving up',
            'impossible', 'hopeless', 'failing', 'behind', 'panic', 'anxiety'
        ]
        self.confusion_keywords = [
            'confused', 'don\'t understand', 'makes no sense', 'stuck',
            'lost', 'help', 'struggling', 'difficult', 'hard'
        ]
    
    def analyze_message(self, message: str, student_id: str) -> Dict[str, Any]:
        # Sentiment analysis
        blob = TextBlob(message)
        vader_scores = sentiment_analyzer.polarity_scores(message)
        
        # Keyword detection
        message_lower = message.lower()
        stress_count = sum(1 for keyword in self.stress_keywords if keyword in message_lower)
        confusion_count = sum(1 for keyword in self.confusion_keywords if keyword in message_lower)
        
        # Calculate wellbeing score (0-10, lower is concerning)
        base_score = 5
        sentiment_adjustment = (vader_scores['compound'] + 1) * 2.5  # Scale to 0-5
        stress_penalty = stress_count * 1.5
        confusion_penalty = confusion_count * 0.5
        
        wellbeing_score = max(0, base_score + sentiment_adjustment - stress_penalty - confusion_penalty)
        
        analysis = {
            'timestamp': datetime.datetime.now().isoformat(),
            'student_id': student_id,
            'message': message,
            'sentiment': {
                'polarity': blob.sentiment.polarity,
                'subjectivity': blob.sentiment.subjectivity,
                'vader': vader_scores
            },
            'wellbeing_score': wellbeing_score,
            'stress_indicators': stress_count,
            'confusion_indicators': confusion_count,
            'flag_for_review': wellbeing_score < 3.0 or stress_count > 2
        }
        
        if analysis['flag_for_review']:
            wellbeing_flags.append(analysis)
            print(f"⚠️  WELLBEING FLAG: Student {student_id} scored {wellbeing_score:.1f}")
        
        return analysis