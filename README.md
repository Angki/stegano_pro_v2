# Steganography Professional

This is a modular steganography application that allows you to hide files within images using two different methods: `append` and `dct`.

## Features

- **Append Mode**: Appends the payload to the end of the image file. The image remains viewable.
- **DCT Mode**: Embeds the payload in the frequency domain of the image using Discrete Cosine Transform. This is more robust against image compression.
- **File & Folder Support**: You can hide a single file or a whole directory (which will be automatically archived).
- **Encryption**: The payload can be encrypted using AES-256-GCM for an extra layer of security.
- **Compression**: The payload is compressed before embedding to maximize capacity.

## Requirements

The following packages are required:
- `Pillow`
- `numpy`
- `cryptography`

You can install them using pip:
```bash
pip install -r requirements.txt
```

## Usage

The application is used via the command line.

### Hiding Files

To hide one or more files, you first need to place them in a single directory. The application will automatically create a TAR archive of the directory.

**General command structure:**

```bash
python cli.py embed -m <mode> -c <cover_image> -p <file_or_directory_to_hide> -o <output_image>
```

- `-m, --mode`: The embedding mode (`append` or `dct`).
- `-c, --container`: The path to the cover image.
- `-p, --payload`: The path to the file or directory to hide.
- `-o, --output`: The path for the output steganographic image.

#### Example: Hiding a single file

To hide a single file named `secret.txt`:

```bash
python cli.py embed -m append -c cover.jpg -p secret.txt -o stego_append.jpg
python cli.py embed -m dct -c cover.jpg -p secret.txt -o stego_dct.jpg
```

#### Example: Hiding multiple files (2-3 files)

1.  Create a directory and move the files you want to hide into it. For example, a directory named `my_secrets` containing `file1.txt`, `file2.txt`, and `image.png`.

    ```
    my_secrets/
    ├── file1.txt
    ├── file2.txt
    └── image.png
    ```

2.  Run the embed command, pointing the payload to the `my_secrets` directory:

    ```bash
    python cli.py embed -m append -c cover.jpg -p my_secrets -o stego_append.jpg
    python cli.py embed -m dct -c cover.jpg -p my_secrets -o stego_dct.jpg
    ```

#### Encryption

To encrypt the payload, add the `--encrypt` flag and provide a password.

You can provide the password via an environment variable:
```bash
export STEGO_PASS="your_secret_password"
python cli.py embed -m dct -c cover.jpg -p my_secrets -o stego_encrypted.jpg --encrypt --pass-env STEGO_PASS
```

Or directly as an argument (less secure):
```bash
python cli.py embed -m dct -c cover.jpg -p my_secrets -o stego_encrypted.jpg --encrypt --password "your_secret_password"
```

### Extracting Files

To extract the hidden files:

```bash
python cli.py extract -s <stego_image> -o <output_directory>
```

- `-s, --stego-image`: The steganographic image.
- `-o, --output-dir`: The directory where the extracted files will be saved.

**Example:**

```bash
python cli.py extract -s stego_append.jpg -o extracted_files
```

If the payload was encrypted, you need to provide the same password during extraction:

```bash
export STEGO_PASS="your_secret_password"
python cli.py extract -s stego_encrypted.jpg -o extracted_files_decrypted --pass-env STEGO_PASS
```

### Other Commands

The application also provides commands for `metrics` and `bench` for performance analysis. Use the `--help` flag to learn more about them.

```bash
python cli.py metrics --help
python cli.py bench --help
```
