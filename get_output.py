import os, sys

def main():
    # Check if a filter key was provided
    if len(sys.argv) < 2:
        print("Usage: python script.py <filter_key>")
        sys.exit(1)

    filter_key = sys.argv[1]

    # List all files and directories in the current directory
    ls = os.listdir()

    # Filter based on the provided key, excluding those with 'dataset' in the name
    output_arg = ' '.join(
        list(filter(lambda x: filter_key in x and 'dataset' not in x, ls))
    )

    # Print the filtered output
    print(output_arg)

if __name__ == "__main__":
    main()
