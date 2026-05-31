"""Fallback extraction helpers for HTML parsing and metric normalization."""
import re
import json
from typing import Optional
from bs4 import BeautifulSoup


class ExtractionFallbacks:
    """Utility methods for extracting data from raw HTML."""

    # Number suffix patterns
    _NUMBER_RE = re.compile(
        r"([\d,]+(?:\.\d+)?)\s*([KkMmBb]?)",
        re.UNICODE,
    )

    # Hashtag pattern
    _HASHTAG_RE = re.compile(r"#([\w\u00C0-\u024F\u0370-\u03FF]+)", re.UNICODE)

    def extract_number(self, text: str) -> int:
        """
        Parse a human-readable number string into an integer.

        Handles comma-separated numbers and K/M/B suffixes.

        Examples:
            "1.2M" -> 1_200_000
            "45.6K" -> 45_600
            "1,234,567" -> 1_234_567
            "2.1B" -> 2_100_000_000
        """
        if not text:
            return 0
        text = text.strip().replace(",", "")
        m = self._NUMBER_RE.search(text)
        if not m:
            return 0
        number = float(m.group(1))
        suffix = m.group(2).upper()
        multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
        return int(number * multipliers.get(suffix, 1))

    def extract_json_ld(self, html: str) -> Optional[dict]:
        """
        Extract and parse the first JSON-LD script block from an HTML page.

        Returns the parsed dict or None if not found.
        """
        soup = BeautifulSoup(html, "lxml")
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, dict):
                    return data
                if isinstance(data, list) and data:
                    return data[0]
            except (json.JSONDecodeError, TypeError):
                continue
        return None

    def extract_og_tags(self, html: str) -> dict:
        """
        Extract Open Graph and Twitter Card meta tags from HTML.

        Returns a flat dict of tag name -> content value.
        """
        soup = BeautifulSoup(html, "lxml")
        og: dict = {}
        for tag in soup.find_all("meta"):
            prop = tag.get("property") or tag.get("name") or ""
            content = tag.get("content", "")
            if prop and content:
                # Normalize: og:title -> og_title, twitter:title -> twitter_title
                key = prop.lower().replace(":", "_").replace("-", "_")
                og[key] = content
        # Also grab regular title
        title_tag = soup.find("title")
        if title_tag and "og_title" not in og:
            og["og_title"] = title_tag.get_text(strip=True)
        return og

    def extract_hashtags(self, text: str) -> list[str]:
        """
        Extract all hashtags from text using regex.

        Returns a deduplicated list of lowercase hashtag strings (without #).
        """
        if not text:
            return []
        matches = self._HASHTAG_RE.findall(text)
        seen: set[str] = set()
        result: list[str] = []
        for tag in matches:
            lower = tag.lower()
            if lower not in seen:
                seen.add(lower)
                result.append(lower)
        return result

    def find_json_in_page(self, html: str, key: str) -> Optional[dict]:
        """
        Search raw HTML for a JSON object containing a specific key.

        Useful for extracting embedded JSON data blobs (e.g. window.__INITIAL_DATA__).

        Args:
            html: Raw page HTML string.
            key: Top-level JSON key to search for.

        Returns:
            Parsed dict if found and key is present, else None.
        """
        # Try to find JSON objects in script tags
        soup = BeautifulSoup(html, "lxml")
        for script in soup.find_all("script"):
            content = script.string
            if not content or key not in content:
                continue
            # Find the outermost JSON object in the script
            start = content.find("{")
            if start == -1:
                continue
            # Walk backward bracket matching
            depth = 0
            for i, ch in enumerate(content[start:], start=start):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            obj = json.loads(content[start : i + 1])
                            if isinstance(obj, dict) and key in obj:
                                return obj
                        except json.JSONDecodeError:
                            break
        return None

    def safe_int(self, value, default: int = 0) -> int:
        """Safely convert a value to int."""
        try:
            return int(str(value).replace(",", "").strip())
        except (ValueError, TypeError):
            return default

    def extract_window_data(self, html: str, var_name: str) -> Optional[dict]:
        """
        Extract window.varName JSON data from script tags.
        
        Common Instagram variables:
        - window._sharedData: Post/profile data with metrics
        - window.__INITIAL_DATA__: Initial page state
        
        Args:
            html: Raw page HTML string.
            var_name: Variable name without 'window.' (e.g., '_sharedData').
        
        Returns:
            Parsed dict if found, else None.
        """
        # Look for window.varName = {...};
        # More robust approach: find start, then count braces to find the end
        start_pattern = rf"window\.{re.escape(var_name)}\s*=\s*\{{"
        start_match = re.search(start_pattern, html)
        if not start_match:
            return None
        
        start_pos = start_match.start()
        # Find the opening brace position
        brace_pos = html.find('{', start_match.end() - 1)
        if brace_pos == -1:
            return None
        
        # Count braces to find the matching closing brace
        depth = 0
        in_string = False
        escape_next = False
        
        for i in range(brace_pos, len(html)):
            ch = html[i]
            
            if escape_next:
                escape_next = False
                continue
            
            if ch == '\\':
                escape_next = True
                continue
            
            if ch == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if in_string:
                continue
            
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    # Found the closing brace
                    try:
                        json_str = html[brace_pos:i+1]
                        return json.loads(json_str)
                    except (json.JSONDecodeError, ValueError):
                        return None
        
        return None

    def extract_instagram_post_metrics(self, html: str) -> Optional[dict]:
        """
        Extract Instagram post/reel metrics from window._sharedData.
        
        Returns a dict with keys: likes, comments, views, caption, 
        author_username, author_id, timestamp, thumbnail_url
        """
        # Try window._sharedData first
        data = self.extract_window_data(html, "_sharedData")
        if not data:
            return None
        
        metrics = {}
        try:
            # Navigate through Instagram's data structure
            # window._sharedData -> entry_data -> PostPage|ReelsPage -> [0] -> graphql -> shortcode_media
            entry_data = data.get("entry_data", {})
            
            # Try PostPage (regular posts)
            post_page = entry_data.get("PostPage", [])
            if post_page and isinstance(post_page, list) and len(post_page) > 0:
                graphql = post_page[0].get("graphql", {})
                media = graphql.get("shortcode_media", {})
                return self._parse_instagram_media(media)
            
            # Try ReelsPage (video reels)
            reels_page = entry_data.get("ReelsPage", [])
            if reels_page and isinstance(reels_page, list) and len(reels_page) > 0:
                graphql = reels_page[0].get("graphql", {})
                media = graphql.get("shortcode_media", {})
                return self._parse_instagram_media(media)
            
            # Try ProfilePage for profile followers
            profile_page = entry_data.get("ProfilePage", [])
            if profile_page and isinstance(profile_page, list) and len(profile_page) > 0:
                graphql = profile_page[0].get("graphql", {})
                user = graphql.get("user", {})
                metrics["followers"] = user.get("edge_followed_by", {}).get("count", 0)
                metrics["posts_count"] = user.get("edge_owner_to_timeline_media", {}).get("count", 0)
                metrics["username"] = user.get("username", "")
                metrics["display_name"] = user.get("full_name", "")
                metrics["bio"] = user.get("biography", "")
                metrics["profile_pic_url"] = user.get("profile_pic_url_hd", user.get("profile_pic_url", ""))
                metrics["verified"] = user.get("is_verified", False)
                return metrics
            
        except (KeyError, TypeError, IndexError):
            pass
        
        return None

    def _parse_instagram_media(self, media: dict) -> dict:
        """Parse Instagram media (post/reel) data structure."""
        metrics = {}
        
        try:
            # Likes
            edge_liked_by = media.get("edge_liked_by", {})
            metrics["likes"] = edge_liked_by.get("count", 0)
            
            # Comments
            edge_comments = media.get("edge_media_to_comment", {})
            metrics["comments"] = edge_comments.get("count", 0)
            
            # Views (for video/reels)
            metrics["views"] = media.get("video_view_count", 0)
            
            # Caption
            caption_edges = media.get("edge_media_to_caption", {}).get("edges", [])
            caption = ""
            if caption_edges and isinstance(caption_edges, list) and len(caption_edges) > 0:
                caption = caption_edges[0].get("node", {}).get("text", "")
            metrics["caption"] = caption
            
            # Author info
            owner = media.get("owner", {})
            metrics["author_username"] = owner.get("username", "")
            metrics["author_id"] = owner.get("id", "")
            metrics["author_followers"] = 0  # Not in post data, use profile endpoint
            
            # Timestamp
            metrics["timestamp"] = media.get("taken_at_timestamp", 0)
            
            # Thumbnail / display image
            metrics["thumbnail_url"] = media.get("display_url", "")
            if not metrics["thumbnail_url"]:
                # Try to get from thumbnail_src
                metrics["thumbnail_url"] = media.get("thumbnail_src", "")
            
            # Is video
            metrics["is_video"] = media.get("is_video", False)
            
        except (KeyError, TypeError):
            pass
        
        return metrics

    def extract_instagram_profile_metrics(self, html: str) -> Optional[dict]:
        """
        Extract Instagram profile metrics from window._sharedData.
        
        Returns a dict with keys: followers, following, posts_count, 
        username, display_name, bio, verified, profile_pic_url
        """
        data = self.extract_window_data(html, "_sharedData")
        if not data:
            return None
        
        metrics = {}
        try:
            entry_data = data.get("entry_data", {})
            profile_page = entry_data.get("ProfilePage", [])
            
            if profile_page and isinstance(profile_page, list) and len(profile_page) > 0:
                graphql = profile_page[0].get("graphql", {})
                user = graphql.get("user", {})
                
                metrics["followers"] = user.get("edge_followed_by", {}).get("count", 0)
                metrics["following"] = user.get("edge_follow", {}).get("count", 0)
                metrics["posts_count"] = user.get("edge_owner_to_timeline_media", {}).get("count", 0)
                metrics["username"] = user.get("username", "")
                metrics["display_name"] = user.get("full_name", "")
                metrics["bio"] = user.get("biography", "")
                metrics["verified"] = user.get("is_verified", False)
                metrics["profile_pic_url"] = user.get("profile_pic_url_hd", user.get("profile_pic_url", ""))
                metrics["user_id"] = user.get("id", "")
                
                return metrics
        except (KeyError, TypeError, IndexError):
            pass
        
        return None


# Singleton instance
extraction_fallbacks = ExtractionFallbacks()

__all__ = ["ExtractionFallbacks", "extraction_fallbacks"]
