"""
Excel Password Handler
Handles sheet protection and password-protected Excel files
"""

import openpyxl
from openpyxl.workbook.protection import WorkbookProtection
import msoffcrypto
import io
import sys

def remove_sheet_protection(input_file, output_file):
    """
    Remove sheet protection from an Excel file.
    Note: This only works for sheet-level protection, not file encryption.
    """
    try:
        # Load the workbook
        wb = openpyxl.load_workbook(input_file)
        
        # Remove protection from all sheets
        for sheet in wb.worksheets:
            if sheet.protection.sheet:
                sheet.protection.sheet = False
                # sheet.protection.password = None
                print(f"Removed protection from sheet: {sheet.title}")
        
        # Remove workbook protection if present
        if wb.security:
            wb.security = WorkbookProtection()
            print("Removed workbook structure protection")
        
        # Save the unprotected workbook
        wb.save(output_file)
        print(f"\nSuccess! Unprotected file saved as: {output_file}")
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    return True

def open_encrypted_file(input_file, password, output_file):
    """
    Open a password-encrypted Excel file and save it without password.
    Requires the correct password.
    """
    try:
        # Open the encrypted file
        with open(input_file, 'rb') as f:
            file = msoffcrypto.OfficeFile(f)
            
            # Provide the password
            file.load_key(password=password)
            
            # Decrypt to a new file
            with open(output_file, 'wb') as decrypted:
                file.decrypt(decrypted)
        
        print(f"Success! Decrypted file saved as: {output_file}")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure you have the correct password and the file is password-encrypted.")
        return False

def main():
    print("Excel Password Handler")
    print("=" * 50)
    print("1. Remove sheet protection (no password needed)")
    print("2. Decrypt password-protected file (password required)")
    print("=" * 50)
    
    choice = input("\nEnter your choice (1 or 2): ").strip()
    
    if choice == "1":
        input_file = input("Enter input Excel file path: ").strip()
        output_file = input("Enter output file path (default: unprotected.xlsx): ").strip()
        if not output_file:
            output_file = "unprotected.xlsx"
        
        remove_sheet_protection(input_file, output_file)
        
    elif choice == "2":
        input_file = input("Enter input Excel file path: ").strip()
        password = input("Enter the password: ").strip()
        output_file = input("Enter output file path (default: decrypted.xlsx): ").strip()
        if not output_file:
            output_file = "decrypted.xlsx"
        
        open_encrypted_file(input_file, password, output_file)
        
    else:
        print("Invalid choice!")
        sys.exit(1)

if __name__ == "__main__":
    # Required libraries (install with pip):
    # pip install openpyxl msoffcrypto-tool
    
    main()
