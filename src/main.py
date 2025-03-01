import os 
import sys
from datetime import  datetime
from collections import defaultdict



class LogAnalysisError(Exception):
    pass

class InvalidLogFormatError(Exception):
    pass



def analyze_logs(log_dir, report_file):

    stats = {
        'processed_files': 0 ,
        'total_entries' : 0 ,
        'log_counts' : defaultdict(int) , 
        'errors' : defaultdict(int) , 
        'error_messages' : defaultdict(int) ,
        'warnings' : []

    }

    try :
        if not os.path.isdir(log_dir):
            raise FileNotFoundError(f"Log directory not found: {log_dir}")
        
        for root , dirs , files in os.walk(log_dir): # yields a tuple (dirpath, dirnames, filenames)
            for filename in files:
                file_path = os.path.join(root , filename)
                # error hanlding 
                try :
                    process_file(file_path , stats)
                except PermissionError:
                    # for permission issues
                    stats['warnings'].append(f"skipped {filename} (permission denied)")
                    stats['errors']['permission'] += 1
                except UnicodeDecodeError:
                    # for encoding issues
                    stats['warnings'].append(f"Skipped {filename} (encoding error)")
                    stats['errors']['encoding'] += 1
                except Exception as e :
                    # for all other errors
                    stats['warnings'].append(f"Skipped {filename} ({str(e)})")
                    stats['errors']['unhandled'] += 1

        generate_report(report_file , stats)



    except Exception as e :
        raise LogAnalysisError(f"Analysis failed: {str(e)}") from e




def process_file(filepath , stats):

    try:
        with open(filepath , 'r' , encoding='utf-8') as f:
            # alternative encoding if need
            try :
                content = f.read()
                # normalize line ending
                content = content.replace('\r\n', '\n').replace('\r', '\n')
                lines = content.split('\n')
            except UnicodeDecodeError:
                f.seek(0)
                lines = f.read().decode('utf-16').splitlines()
        
        #empy files
        if not any(line.strip() for line in lines):
            stats['warnings'].append(f"Empty file: {os.path.basename(filepath)}")
            stats['errors']['empty'] += 1
            return
        
        stats['processed_files'] += 1

        for line_num, line in enumerate(lines, 1):
            try:
                # validate line format
                if not line.strip():
                    continue

                parts = line.strip().split()
                if len(parts) < 4:
                    raise InvalidLogFormatError("Incomplete log entry")

                timestamp_str = f"{parts[0]} {parts[1]}"
                level = parts[2]
                message = ' '.join(parts[3:])                

                # validate timestamp
                try:
                    datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    raise InvalidLogFormatError(f"Invalid timestamp in line {line_num}")

                # update statistics
                stats['log_counts'][level] += 1
                stats['total_entries'] += 1

                if level == 'ERROR':
                    stats['error_messages'][message] += 1

            except InvalidLogFormatError as e:
                print(f"Bad line: {line.strip()}") #DEBUGING
                stats['warnings'].append(f"{os.path.basename(filepath)} line {line_num}: {str(e)}")
                stats['errors']['format'] += 1

    except IsADirectoryError:
        pass # skip directories
    except PermissionError:
        raise
    except Exception as e:
        stats['warnings'].append(f"Failed to process {os.path.basename(filepath)}: {str(e)}")
        stats['errors']['processing'] += 1




def generate_report(report_file, stats):
 
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            # header
            f.write(f"Log Analysis Report - {datetime.now().isoformat()}\n")
            f.write("=" * 40 + "\n\n")

            # file statistics
            f.write(f"Files processed: {stats['processed_files']}\n")
            f.write(f"Total log entries: {stats['total_entries']}\n")

            # error rate calculation
            if stats['total_entries'] > 0:
                error_rate = (stats['log_counts']['ERROR'] / stats['total_entries']) * 100
                f.write(f"Error rate: {error_rate:.1f}%\n\n")
            else:
                f.write("No valid log entries found\n\n")

            # log type breakdown
            f.write("Log Type Counts:\n")
            for level, count in stats['log_counts'].items():
                if stats['total_entries'] > 0:
                    percentage = (count / stats['total_entries']) * 100
                    f.write(f"- {level}: {count} ({percentage:.1f}%)\n")

            # most common error
            if stats['error_messages']:
                common_error = max(stats['error_messages'].items(), key=lambda x: x[1])
                f.write(f"\nMost Common Error: {common_error[0]} ({common_error[1]} occurrences)\n")

            # error and warning details
            if stats['warnings']:
                f.write("\nWarnings:\n")
                for warning in stats['warnings'][:5]:  # Show top 5 warnings
                    f.write(f"- {warning}\n")
                if len(stats['warnings']) > 5:
                    f.write(f"- ...({len(stats['warnings']) - 5} more warnings)\n")

    except IOError as e:
        raise LogAnalysisError(f"Failed to write report: {str(e)}")

if __name__ == "__main__":
    try:
        analyze_logs("logs/", "report.txt")
        print("Analysis completed successfully")
    except LogAnalysisError as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)