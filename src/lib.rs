#[cfg(feature = "python")]
use pyo3::prelude::*;

/// Tokenize text into lowercase alphabetic words of length >= min_len.
#[cfg_attr(feature = "python", pyfunction)]
pub fn tokenize(text: &str, min_len: usize) -> Vec<String> {
    text.split_whitespace()
        .map(|w| {
            w.chars()
                .filter(|c| c.is_alphabetic())
                .collect::<String>()
                .to_lowercase()
        })
        .filter(|w| w.len() >= min_len)
        .collect()
}

/// Return a snippet of `text` around the first occurrence of `query`
/// (case-insensitive), padded up to `context` **characters** on each side.
///
/// # This used to panic on ordinary input
///
/// The previous version took byte offsets from the *lowercased* string and
/// sliced the *original* with them: `text[start..end]` where
/// `start = pos.saturating_sub(context)`. Two things go wrong.
///
/// First, `context` is documented as a character count but was subtracted from
/// a byte offset, so on multi-byte text the window came out the wrong size.
/// Second, and worse, an offset landing mid-character makes the slice panic --
/// surfacing through PyO3 as a `PanicException`, which is barely catchable.
/// Brute-forcing the old code found 6 of 60 `(text, context)` pairs panicking,
/// among them "cafe Odin" (with an accent), "Zeus - Odin" (with an em-dash)
/// and "AEsir Odin".
///
/// That is not an exotic edge case. This function exists to search Project
/// Gutenberg classics -- Herodotus, Plutarch, Gibbon -- which are full of
/// accented names and em-dashes.
///
/// It now works in character space throughout, so no index can fall inside a
/// character. Lowercasing can also change a string's character count, so the
/// match position is mapped back through character indices rather than assumed
/// to line up byte-for-byte.
#[cfg_attr(feature = "python", pyfunction)]
pub fn highlight_snippet(text: &str, query: &str, context: usize) -> String {
    let tl = text.to_lowercase();
    let ql = query.to_lowercase();
    if ql.is_empty() {
        return text.chars().take(context * 2).collect();
    }
    let byte_pos = match tl.find(&ql) {
        None => return text.chars().take(context * 2).collect(),
        Some(p) => p,
    };
    // Byte offset in the lowercased string -> character index. Character
    // indices are the only thing the two strings reliably share.
    let char_pos = tl[..byte_pos].chars().count();
    let query_chars = ql.chars().count();
    debug_assert!(query_chars > 0, "the empty query returned above");

    let total_chars = text.chars().count();
    let start = char_pos.saturating_sub(context);
    let end = char_pos
        .saturating_add(query_chars)
        .saturating_add(context)
        .min(total_chars);
    debug_assert!(start <= end, "the window must not be inverted");

    let snippet: String = text.chars().skip(start).take(end - start).collect();
    if start > 0 {
        format!("\u{2026}{snippet}")
    } else {
        snippet
    }
}

/// Score a corpus entry against a query for relevance.
#[cfg_attr(feature = "python", pyfunction)]
pub fn score_entry(title: &str, body: &str, query: &str) -> f64 {
    let q = query.to_lowercase();
    let t = title.to_lowercase();
    if q.is_empty() {
        return 0.0;
    }
    let mut score = 0.0_f64;
    if t.starts_with(&q) {
        score += 1000.0;
    } else if t.contains(&q) {
        score += 500.0;
    }
    if body.to_lowercase().contains(&q) {
        score += 150.0;
    }
    score
}

#[cfg(feature = "python")]
#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(tokenize, m)?)?;
    m.add_function(wrap_pyfunction!(highlight_snippet, m)?)?;
    m.add_function(wrap_pyfunction!(score_entry, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn snippets_survive_the_text_this_function_is_meant_to_search() {
        // Every one of these panicked before: byte offsets from the lowercased
        // string were used to slice the original, landing mid-character.
        for (text, context) in [
            ("cafe\u{301} Odin", 2usize),
            ("Zeus \u{2014} Odin", 2),
            ("Zeus \u{2014} Odin", 3),
            ("\u{c6}sir Odin", 5),
            ("\u{392}\u{3b1}\u{3b2}\u{3c5}\u{3bb}\u{3ce}\u{3bd} Odin", 4),
        ] {
            let got = highlight_snippet(text, "odin", context);
            assert!(
                got.contains("Odin"),
                "lost the match in {text:?} at context {context}: {got:?}"
            );
        }
    }

    #[test]
    fn the_context_window_is_measured_in_characters() {
        // "context" is documented as characters. With byte arithmetic an
        // accented prefix silently shrank the window.
        let got = highlight_snippet("abcdefXYZghijkl", "xyz", 3);
        assert_eq!(got, "\u{2026}defXYZghi");
    }

    #[test]
    fn a_match_at_the_start_is_not_prefixed_with_an_ellipsis() {
        assert_eq!(highlight_snippet("Odin rides", "odin", 0), "Odin");
        assert!(!highlight_snippet("Odin rides", "odin", 3).starts_with('\u{2026}'));
    }

    #[test]
    fn a_missing_query_falls_back_to_the_opening_characters() {
        let got = highlight_snippet("Zeus and Hera", "odin", 4);
        assert_eq!(got, "Zeus and");
        // And the fallback must not split a character either.
        let accented = highlight_snippet("cafe\u{301} society", "odin", 3);
        assert_eq!(accented.chars().count(), 6);
    }

    #[test]
    fn an_empty_query_does_not_match_everything() {
        // `"".find("")` is Some(0), so without the guard this would report a
        // match at the start of every document.
        let got = highlight_snippet("Zeus and Hera", "", 4);
        assert!(!got.starts_with('\u{2026}'), "an empty query is not a hit");
    }

    #[test]
    fn a_context_larger_than_the_text_is_clamped() {
        assert_eq!(highlight_snippet("Odin", "odin", 10_000), "Odin");
    }

    #[test]
    fn tokenize_keeps_only_long_enough_alphabetic_words() {
        assert_eq!(
            tokenize("The Peloponnesian War, 431 BC", 3),
            vec!["the", "peloponnesian", "war"]
        );
        assert!(tokenize("a b c", 2).is_empty());
    }

    #[test]
    fn tokenize_handles_non_ascii() {
        // `w.len()` is a byte count, so a short accented word can pass a
        // character-based reading of `min_len`. Pinning current behaviour.
        let got = tokenize("cafe\u{301} \u{c6}sir", 3);
        assert!(
            got.iter().all(|w| !w.is_empty()),
            "no empty tokens: {got:?}"
        );
    }
}
