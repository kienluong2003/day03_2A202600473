from typing import Dict, List


# Mock dataset used for lab exercises.
HOTEL_REVIEWS: Dict[str, List[Dict[str, object]]] = {
	"HCM001": [
		{"rating": 4.8, "comment": "Very clean room, friendly staff, good breakfast."},
		{"rating": 4.6, "comment": "Great location near downtown, comfortable bed."},
		{"rating": 4.2, "comment": "Nice service but the elevator was slow."},
		{"rating": 4.7, "comment": "Excellent value and quiet at night."},
	],
	"HAN002": [
		{"rating": 3.9, "comment": "Convenient location but room felt small."},
		{"rating": 4.1, "comment": "Helpful front desk and quick check-in."},
		{"rating": 3.7, "comment": "Breakfast was average, wifi was unstable."},
		{"rating": 4.0, "comment": "Good for business trips, clean and safe."},
	],
	"DAD003": [
		{"rating": 4.9, "comment": "Amazing sea view and super clean facilities."},
		{"rating": 4.7, "comment": "Staff were excellent, spa service was perfect."},
		{"rating": 4.8, "comment": "Large room, great breakfast, family friendly."},
	],
}


THEME_KEYWORDS: Dict[str, List[str]] = {
	"cleanliness": ["clean", "dirty", "hygiene"],
	"staff": ["staff", "service", "front desk"],
	"location": ["location", "downtown", "near", "central"],
	"food": ["breakfast", "food", "restaurant"],
	"comfort": ["bed", "quiet", "room", "noise"],
	"internet": ["wifi", "internet"],
	"value": ["value", "price", "cost"],
}


def _extract_top_themes(comments: List[str]) -> List[str]:
	joined = " ".join(c.lower() for c in comments)
	scores: Dict[str, int] = {}

	for theme, keywords in THEME_KEYWORDS.items():
		scores[theme] = sum(joined.count(keyword) for keyword in keywords)

	ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
	return [theme for theme, score in ranked if score > 0][:3]


def get_hotel_reviews(hotel_id: str) -> str:
	"""
	Return a compact summary of customer reviews for a hotel.

	Args:
		hotel_id: Hotel identifier (for example: HCM001, HAN002, DAD003).

	Returns:
		A text summary containing average rating and key review themes.
	"""
	if not hotel_id:
		return "Invalid hotel_id. Please provide a non-empty hotel id."

	normalized_id = hotel_id.strip().upper()
	reviews = HOTEL_REVIEWS.get(normalized_id)

	if not reviews:
		return f"No review data found for hotel_id={normalized_id}."

	ratings = [float(item["rating"]) for item in reviews]
	comments = [str(item["comment"]) for item in reviews]

	average_rating = sum(ratings) / len(ratings)
	top_themes = _extract_top_themes(comments)
	theme_text = ", ".join(top_themes) if top_themes else "general satisfaction"

	sample_comments = comments[:2]
	sample_text = " | ".join(sample_comments)

	return (
		f"Hotel {normalized_id}: average rating {average_rating:.1f}/5 from {len(reviews)} reviews. "
		f"Common themes: {theme_text}. "
		f"Sample feedback: {sample_text}"
	)

