use pyo3::prelude::*;

/// Tokenize text into lowercase alphabetic words of length >= min_len.
#[pyfunction]
fn tokenize(text: &str, min_len: usize) -> Vec<String> {
    text.split_whitespace()
        .map(|w| w.chars().filter(|c| c.is_alphabetic()).collect::<String>().to_lowercase())
        .filter(|w| w.len() >= min_len)
        .collect()
}

/// Return a snippet of `text` around the first occurrence of `query` (case-insensitive).
/// Pads up to `context` chars on each side.
#[pyfunction]
fn highlight_snippet(text: &str, query: &str, context: usize) -> String {
    let tl = text.to_lowercase();
    let ql = query.to_lowercase();
    match tl.find(&ql) {
        None => text.chars().take(context * 2).collect(),
        Some(pos) => {
            let start = pos.saturating_sub(context);
            let end = (pos + ql.len() + context).min(text.len());
            let snippet: String = text[start..end].to_string();
            if start > 0 { format!("\u{2026}{}", snippet) } else { snippet }
        }
    }
}

/// Score a corpus entry against a query for relevance.
#[pyfunction]
fn score_entry(title: &str, body: &str, query: &str) -> f64 {
    let q = query.to_lowercase();
    let t = title.to_lowercase();
    if q.is_empty() { return 0.0; }
    let mut score = 0.0_f64;
    if t.starts_with(&q)   { score += 1000.0; }
    else if t.contains(&q) { score += 500.0; }
    if body.to_lowercase().contains(&q) { score += 150.0; }
    score
}

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(tokenize, m)?)?;
    m.add_function(wrap_pyfunction!(highlight_snippet, m)?)?;
    m.add_function(wrap_pyfunction!(score_entry, m)?)?;
    Ok(())
}
