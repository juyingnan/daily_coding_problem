#!/usr/bin/env python3
import sys
import fitz  # PyMuPDF

def extract_annotations(pdf_path, output_txt):
    # Open the PDF file
    doc = fitz.open(pdf_path)
    with open(output_txt, "w", encoding="utf-8") as f:
        # Loop through each page
        for page_number in range(len(doc)):
            page = doc[page_number]
            annot = page.first_annot
            # Process all annotations on the page
            while annot:
                # Retrieve the comment content (if any)
                comment = annot.info.get("content", "").strip()
                associated_text = ""
                # Check if the annotation provides vertices (common in highlights)
                if annot.vertices:
                    # vertices are provided as a list of points, grouped in quads (4 points per quad)
                    quads = [annot.vertices[i:i+4] for i in range(0, len(annot.vertices), 4)]
                    texts = []
                    for quad in quads:
                        # Create a Quad object and get its bounding rectangle
                        q = fitz.Quad(quad)
                        rect = q.rect
                        # Extract the text in the region defined by this rectangle
                        text = page.get_text("text", clip=rect).strip()
                        texts.append(text)
                    associated_text = " ".join(texts)
                else:
                    # For annotations without vertices (e.g. sticky notes), use the annotation's rectangle
                    associated_text = page.get_text("text", clip=annot.rect).strip()
                
                # Only write out if there's a comment present
                if comment:
                    f.write(f"Page {page_number + 1}: {comment}\n")
                    f.write(f"Associated Text: {associated_text}\n\n")
                annot = annot.next  # Move to the next annotation on the page

if __name__ == '__main__':
    # Usage: python extract_comments.py input.pdf output.txt
    if len(sys.argv) != 3:
        print("Usage: python extract_comments.py input.pdf output.txt")
        sys.exit(1)
    pdf_path = sys.argv[1]
    output_txt = sys.argv[2]
    extract_annotations(pdf_path, output_txt)
    print(f"Annotations extracted to {output_txt}")
