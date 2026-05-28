# Skill: Add Blog Entry

Use this skill whenever the user requests to manually add a new scientific paper to the portfolio and blog website.

## Requirements

1. **Write a Plain-Language Explanation**:
   Generate an educational, jargon-free 3-5 minute read explaining the paper to a non-expert.
   - **Structure**: Introductory hook -> The core problem -> The model/approach -> Key results and benchmarks -> "## Key Takeaways" bullet list (3-5 bullets).
   - **Visuals**: Include one detailed Mermaid diagram representing the architecture or workflow of the model.
   - **Length**: ~400 words.
   - **Style**: Science communicator tone. Avoid using prefixes like "Didactic Breakdown:".

2. **Run `scripts/add_paper.py`**:
   Add the paper to `data/posts.json` using the CLI script. Specify the pre-generated explanation in a file.
   - Command format:
     ```bash
     export PYTHONPATH="."
     pixi run -e dev python scripts/add_paper.py \
       --title "Paper Title" \
       --abstract "Full abstract text..." \
       --authors "Author 1, Author 2, Author 3" \
       --link "arXiv URL" \
       --date "YYYY-MM-DD" \
       --category "One of: Weather Forecasting, Subseasonal to Seasonal Forecasting, Climate Emulation, Data Assimilation, Downscaling" \
       --explanation-file "/path/to/explanation.md"
     ```

3. **Re-compile the Blog**:
   Run `compile_blog.py` to regenerate the blog database structure:

   ```bash
   export PYTHONPATH="."
   pixi run -e dev compile
   ```

4. **Verify formatting**:
   Run `pre-commit` to ensure everything meets style and format guidelines:
   ```bash
   export PYTHONPATH="."
   pixi run -e dev pre-commit run --all-files
   ```
