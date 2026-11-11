# medsplit

medsplit splits medical-record PDFs into smaller PDFs and files them by date of service. It puts subpoenas, deposition by written questions (DWQ), and related paperwork in a separate folder. Your original PDFs stay in place and are never modified. Processing happens on your computer.

## Install medsplit

### 1. Install uv

uv installs medsplit and the Python packages it needs. If `uv --version` already prints a version number, skip to step 2.

**macOS or Linux:** Open Terminal and run:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:** Open PowerShell and run:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close and reopen Terminal or PowerShell, then run `uv --version` to check the installation. See the [official uv installation guide](https://docs.astral.sh/uv/getting-started/installation/) for other installation methods.

### 2. Clone the GitHub repository and install medsplit

1. If `git --version` does not print a version number, install [Git](https://git-scm.com/install/) for your operating system, then reopen Terminal or PowerShell.
2. Open the medsplit repository on GitHub. Click **Code → HTTPS** and copy the repository URL. If the repository is private, sign in with a GitHub account that has access.
3. In Terminal or PowerShell, use `cd` to go to the folder where you want to keep the repository. For example, `cd "$HOME/Downloads"` works on macOS, Linux, and Windows PowerShell.
4. Run these commands, replacing `PASTE-THE-HTTPS-URL-HERE` with the URL you copied. Keep the quotes. If Git asks you to sign in, use the account that has access to the repository.

```sh
git clone "PASTE-THE-HTTPS-URL-HERE" medsplit
cd medsplit
```

5. Run the following commands from the `medsplit` folder, which contains `pyproject.toml`. The dot after `install` tells uv to install medsplit from this folder.

```sh
uv tool install .
medsplit --help
```

If the terminal can’t find `medsplit`, run `uv tool update-shell`, close and reopen the terminal, and try `medsplit --help` again. If your shell still can’t find it, `uv tool dir --bin` shows the folder to add to your PATH, the list of folders your shell searches for commands.

After installation, you can run `medsplit` from any folder. To install a newer version, return to the cloned `medsplit` folder and run `git pull`. Once that finishes successfully, run `uv tool install --force .`.

### 3. Install Tesseract for scanned PDFs

Tesseract lets medsplit read text from scanned pages using optical character recognition (OCR). Install it separately from medsplit.

| System                                  | Installation                                                                                                                                                                                                                         |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| macOS with [Homebrew](https://brew.sh/) | Run `brew install tesseract`.                                                                                                                                                                                                        |
| Ubuntu or Debian                        | Run `sudo apt install tesseract-ocr tesseract-ocr-eng`.                                                                                                                                                                              |
| Fedora                                  | Run `sudo dnf install tesseract tesseract-langpack-eng`.                                                                                                                                                                             |
| Windows                                 | Follow the Windows instructions in the [Tesseract installation guide](https://tesseract-ocr.github.io/tessdoc/Installation.html). Include the English language data and add the folder containing `tesseract.exe` to your user PATH. |

Open a new terminal and run `tesseract --list-langs`. Check that `eng` appears in the list. On Windows, if Tesseract is installed in the default location but the command is missing, search the Start menu for **Edit environment variables for your account**, edit **Path**, and add `C:\Program Files\Tesseract-OCR`. Then open a new PowerShell window.

If your PDFs already have selectable text and you want to skip OCR, run medsplit with `--no-ocr`. Image-only pages may then be harder to date and will not gain searchable text.

## Split your PDFs

Put the PDFs you want to process directly in one folder. medsplit reads the PDFs in that folder and skips subfolders. Give it the folder path in quotes.

**macOS or Linux**

```sh
medsplit "$HOME/Documents/Case Records"
```

**Windows PowerShell**

```powershell
medsplit "$HOME\Documents\Case Records"
```

Replace the example path with your records folder. If your terminal is already in that folder, type just `medsplit`.

## Find and review the results

Open `split_files` inside the folder you processed.

| Item                            | What it contains                                                                                                                                           |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Date folders such as `20240304` | Records assigned to that date (March 4, 2024 in this example). Separate encounters on the same date can appear as separate PDFs.                           |
| `_DWQ_and_Subpoenas`            | Pages identified as legal paperwork, such as subpoenas, DWQs, affidavits, and cover sheets.                                                                |
| `_Undated`                      | Medical pages that medsplit could not assign a date to.                                                                                                    |
| `_index.csv`                    | A page-by-page index you can open in Excel or another spreadsheet app. It shows the source PDF, page number, Bates number, assigned date, and output file. |

Output filenames use the first and last Bates numbers when available. Otherwise, they use the original filename and page range.

Spot-check the split PDFs and the index before relying on the results. Pages without a date can inherit the previous page’s date. In the index, the `date_source` column shows how medsplit chose the date. If the terminal says a PDF was skipped, check that file separately.

## Common options

| Command                             | What it does                                                                                                                   |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `medsplit --help`                   | Shows all options.                                                                                                             |
| `medsplit --bates-prefix "PLA MED"` | Looks for Bates stamps beginning with `PLA MED`. The default is `DEF DWQ`.                                                     |
| `medsplit --no-ocr`                 | Processes the PDFs without OCR.                                                                                                |
| `medsplit --overwrite`              | Deletes the existing `split_files` folder and recreates it. Move or rename that folder first if you want to keep its contents. |

These examples assume your terminal is already in the records folder. You can also include the folder path, for example `medsplit "Case Records" --bates-prefix "PLA MED"`.
