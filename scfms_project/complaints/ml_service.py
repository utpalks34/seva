# complaints/ml_service.py
"""
Machine Learning service for detecting duplicate civic complaints.
Uses TF-IDF vectorisation + cosine similarity (scikit-learn).
"""

import logging
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class DuplicateDetectionService:
    """Detect near-duplicate complaints using TF-IDF + Cosine Similarity."""

    # ------------------------------------------------------------------ #
    #  FIND SIMILAR COMPLAINTS                                             #
    # ------------------------------------------------------------------ #
    @staticmethod
    def find_similar_complaints(complaint_text: str, threshold: float = 0.55, limit: int = 5):
        """
        Return the most similar existing complaints to ``complaint_text``.

        Args:
            complaint_text: title + description of the new complaint
            threshold:      minimum cosine-similarity score (0–1)
            limit:          maximum number of results to return

        Returns:
            list of dicts – {complaint, similarity_score, similarity_percentage}
        """
        # Lazy import to avoid circular imports at module load time
        from .models import Complaint

        try:
            existing = list(
                Complaint.objects.filter(is_duplicate=False)
                                 .values('id', 'title', 'description', 'status', 'created_at')
            )
            if not existing:
                return []

            # Build corpus: existing complaints + the new text at the end
            corpus = [f"{c['title']} {c['description']}" for c in existing]
            corpus.append(complaint_text)

            vectorizer = TfidfVectorizer(
                lowercase=True,
                stop_words='english',
                ngram_range=(1, 2),
                max_features=500,
            )
            tfidf_matrix = vectorizer.fit_transform(corpus)

            # Cosine similarity of the last row (new complaint) vs all existing
            scores = cosine_similarity(tfidf_matrix[-1:], tfidf_matrix[:-1])[0]

            # Filter by threshold
            above = np.where(scores >= threshold)[0]
            if len(above) == 0:
                logger.info(f"No duplicate candidates found (threshold={threshold})")
                return []

            # Sort descending by score, take top `limit`
            sorted_idx = above[np.argsort(-scores[above])][:limit]

            results = []
            for idx in sorted_idx:
                try:
                    complaint_obj = Complaint.objects.get(id=existing[idx]['id'])
                    results.append({
                        'complaint': complaint_obj,
                        'similarity_score': float(scores[idx]),
                        'similarity_percentage': round(float(scores[idx]) * 100, 1),
                    })
                except Complaint.DoesNotExist:
                    continue

            logger.info(f"Found {len(results)} similar complaint(s)")
            return results

        except Exception as exc:
            logger.error(f"Duplicate detection error: {exc}")
            return []

    # ------------------------------------------------------------------ #
    #  MARK AS DUPLICATE                                                   #
    # ------------------------------------------------------------------ #
    @staticmethod
    def mark_as_duplicate(original_complaint_id: int, duplicate_complaint_id: int) -> bool:
        """
        Mark ``duplicate_complaint_id`` as a duplicate of ``original_complaint_id``.
        Sends a notification to the citizen who filed the duplicate.
        """
        from .models import Complaint
        from .utils import create_notification

        try:
            original  = Complaint.objects.get(id=original_complaint_id)
            duplicate = Complaint.objects.get(id=duplicate_complaint_id)

            duplicate.is_duplicate       = True
            duplicate.original_complaint = original
            duplicate.save(update_fields=['is_duplicate', 'original_complaint'])

            # Notify the citizen
            create_notification(
                user=duplicate.user,
                message=(
                    f"Your complaint \"{duplicate.title}\" has been identified as a duplicate "
                    f"of complaint #{original.id}: \"{original.title}\". "
                    f"Both will be tracked together."
                ),
                complaint=duplicate,
            )

            logger.info(f"Marked complaint #{duplicate_complaint_id} as duplicate of #{original_complaint_id}")
            return True

        except Complaint.DoesNotExist as exc:
            logger.error(f"Complaint not found while marking duplicate: {exc}")
            return False
        except Exception as exc:
            logger.error(f"Error marking duplicate: {exc}")
            return False
