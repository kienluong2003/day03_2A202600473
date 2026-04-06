"""
Hotel Details Tool using Local LLM Model.

This tool uses a local LLM model to generate detailed information about a specific hotel,
including amenities, facilities, images description, and hotel policies.
"""

import re
from typing import Dict, Any, List, Optional
from src.core.llm_provider import LLMProvider


class HotelDetailsTool:
    """
    A tool that uses a local LLM to retrieve detailed information about a specific hotel,
    including amenities (pool, gym, spa, etc.), image descriptions, and policies.
    """

    def __init__(self, llm: LLMProvider):
        """
        Initialize the Hotel Details Tool.

        Args:
            llm: An instance of LLMProvider (LocalProvider, OpenAI, Gemini, etc.)
        """
        self.llm = llm
        self.name = "get_hotel_details"
        self.description = (
            "Get detailed information about a specific hotel including amenities "
            "(pool, gym, spa, restaurant, etc.), image descriptions, and hotel policies "
            "(check-in/out times, cancellation policy, pet policy, etc.)."
        )

    def execute(self, hotel_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific hotel.

        Args:
            hotel_id: The unique identifier of the hotel
                      (e.g., "HTL-001", "grand-hyatt-hanoi", "marriott-hcm-001")

        Returns:
            Dictionary with hotel detail information:
            {
                "hotel_id": str,
                "hotel_name": str,
                "star_rating": str,
                "amenities": {
                    "has_pool": bool,
                    "has_gym": bool,
                    "has_spa": bool,
                    "has_restaurant": bool,
                    "has_bar": bool,
                    "has_wifi": bool,
                    "has_parking": bool,
                    "has_airport_shuttle": bool,
                    "has_business_center": bool,
                    "has_kids_club": bool,
                    "other_amenities": List[str]
                },
                "images_description": List[str],
                "policies": {
                    "check_in_time": str,
                    "check_out_time": str,
                    "cancellation_policy": str,
                    "pet_policy": str,
                    "smoking_policy": str,
                    "extra_bed_policy": str
                },
                "description": str,
                "raw_response": str,
                "model": str,
                "latency_ms": float
            }
        """
        # Create a structured prompt for the LLM
        prompt = f"""Provide detailed information about the hotel with ID: {hotel_id}.

        Format your response with these exact labels on separate lines:

        Hotel Name: [full hotel name]
        Star Rating: [1-5 stars]
        Description: [2-3 sentence overview of the hotel]

        AMENITIES:
        Has Pool: [Yes/No]
        Has Gym: [Yes/No]
        Has Spa: [Yes/No]
        Has Restaurant: [Yes/No]
        Has Bar: [Yes/No]
        Has WiFi: [Yes/No]
        Has Parking: [Yes/No]
        Has Airport Shuttle: [Yes/No]
        Has Business Center: [Yes/No]
        Has Kids Club: [Yes/No]
        Other Amenities: [comma-separated list of additional amenities]

        IMAGES:
        Image 1: [description of lobby/exterior]
        Image 2: [description of a room type]
        Image 3: [description of a facility or view]

        POLICIES:
        Check-in Time: [time, e.g., 14:00]
        Check-out Time: [time, e.g., 12:00]
        Cancellation Policy: [brief policy description]
        Pet Policy: [allowed/not allowed + conditions]
        Smoking Policy: [smoking/non-smoking policy]
        Extra Bed Policy: [availability and cost]

        Keep the response structured and concise."""

        system_prompt = """You are a hotel information assistant with extensive knowledge of 
        hotels worldwide. Provide accurate and detailed hotel information based on the hotel ID 
        provided. If the exact hotel is unknown, generate realistic and plausible information 
        consistent with what that hotel type and location would typically offer. Always maintain 
        a professional, informative tone suitable for travelers."""

        # Call the LLM
        response = self.llm.generate(prompt, system_prompt)
        content = response["content"]

        # Parse the structured response
        parsed_details = self._parse_hotel_details_response(content, hotel_id)
        parsed_details["raw_response"] = content
        parsed_details["model"] = self.llm.model_name
        parsed_details["latency_ms"] = response["latency_ms"]

        return parsed_details

    def _parse_hotel_details_response(
        self, response: str, hotel_id: str
    ) -> Dict[str, Any]:
        """
        Parse the LLM response to extract structured hotel detail data.

        Args:
            response: The raw response from the LLM
            hotel_id: The requested hotel ID

        Returns:
            Dictionary with parsed hotel detail information
        """
        details: Dict[str, Any] = {
            "hotel_id": hotel_id,
            "hotel_name": "Not available",
            "star_rating": "Not available",
            "description": "Not available",
            "amenities": {
                "has_pool": False,
                "has_gym": False,
                "has_spa": False,
                "has_restaurant": False,
                "has_bar": False,
                "has_wifi": False,
                "has_parking": False,
                "has_airport_shuttle": False,
                "has_business_center": False,
                "has_kids_club": False,
                "other_amenities": [],
            },
            "images_description": [],
            "policies": {
                "check_in_time": "Not available",
                "check_out_time": "Not available",
                "cancellation_policy": "Not available",
                "pet_policy": "Not available",
                "smoking_policy": "Not available",
                "extra_bed_policy": "Not available",
            },
        }

        # ── Basic info ────────────────────────────────────────────────────────
        hotel_name_match = re.search(
            r"Hotel\s*Name:\s*(.+?)(?:\n|$)", response, re.IGNORECASE
        )
        if hotel_name_match:
            details["hotel_name"] = hotel_name_match.group(1).strip()

        star_match = re.search(
            r"Star\s*Rating:\s*(.+?)(?:\n|$)", response, re.IGNORECASE
        )
        if star_match:
            details["star_rating"] = star_match.group(1).strip()

        desc_match = re.search(
            r"Description:\s*(.+?)(?:\n(?:[A-Z])|$)", response, re.IGNORECASE | re.DOTALL
        )
        if desc_match:
            details["description"] = desc_match.group(1).strip()

        # ── Amenities (Yes/No flags) ──────────────────────────────────────────
        amenity_fields = {
            "has_pool": r"Has\s*Pool:\s*(.+?)(?:\n|$)",
            "has_gym": r"Has\s*Gym:\s*(.+?)(?:\n|$)",
            "has_spa": r"Has\s*Spa:\s*(.+?)(?:\n|$)",
            "has_restaurant": r"Has\s*Restaurant:\s*(.+?)(?:\n|$)",
            "has_bar": r"Has\s*Bar:\s*(.+?)(?:\n|$)",
            "has_wifi": r"Has\s*WiFi:\s*(.+?)(?:\n|$)",
            "has_parking": r"Has\s*Parking:\s*(.+?)(?:\n|$)",
            "has_airport_shuttle": r"Has\s*Airport\s*Shuttle:\s*(.+?)(?:\n|$)",
            "has_business_center": r"Has\s*Business\s*Center:\s*(.+?)(?:\n|$)",
            "has_kids_club": r"Has\s*Kids\s*Club:\s*(.+?)(?:\n|$)",
        }

        for key, pattern in amenity_fields.items():
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                value = match.group(1).strip().lower()
                details["amenities"][key] = value.startswith("yes")

        # Other amenities (comma-separated list)
        other_match = re.search(
            r"Other\s*Amenities:\s*(.+?)(?:\n|$)", response, re.IGNORECASE
        )
        if other_match:
            raw_others = other_match.group(1).strip()
            details["amenities"]["other_amenities"] = [
                item.strip()
                for item in raw_others.split(",")
                if item.strip() and item.strip().lower() != "none"
            ]

        # ── Images ───────────────────────────────────────────────────────────
        image_matches = re.findall(
            r"Image\s*\d+:\s*(.+?)(?:\n|$)", response, re.IGNORECASE
        )
        details["images_description"] = [img.strip() for img in image_matches]

        # ── Policies ─────────────────────────────────────────────────────────
        policy_fields = {
            "check_in_time": r"Check-?in\s*Time:\s*(.+?)(?:\n|$)",
            "check_out_time": r"Check-?out\s*Time:\s*(.+?)(?:\n|$)",
            "cancellation_policy": r"Cancellation\s*Policy:\s*(.+?)(?:\n|$)",
            "pet_policy": r"Pet\s*Policy:\s*(.+?)(?:\n|$)",
            "smoking_policy": r"Smoking\s*Policy:\s*(.+?)(?:\n|$)",
            "extra_bed_policy": r"Extra\s*Bed\s*Policy:\s*(.+?)(?:\n|$)",
        }

        for key, pattern in policy_fields.items():
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                details["policies"][key] = match.group(1).strip()

        return details

    def to_tool_dict(self) -> Dict[str, Any]:
        """
        Return tool definition as a dictionary for use in the ReAct agent.

        Returns:
            Tool definition with name, description, and parameters
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "hotel_id": (
                    "The unique identifier of the hotel to retrieve details for "
                    "(e.g., 'HTL-001', 'grand-hyatt-hanoi', 'marriott-hcm-001')"
                )
            },
        }