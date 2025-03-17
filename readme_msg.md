Collecting workspace information

# WeChatMsg Project Overview

This project is designed to read, parse, and display WeChat chat history from local databases. Let me explain the key components of how it loads WeChat chat records:

## Database Structure

The project works with several SQLite databases that WeChat stores locally:

1. **MSG database**: Contains the actual chat messages
2. **MicroMsg database**: Contains contact information
3. **MediaMSG database**: Contains voice messages
4. **Other databases**: For images, files, etc.

## Loading Process

From examining the code, the process to read WeChat chat history involves:

1. **Decryption**: WeChat databases are encrypted with AES, and the project decrypts them first
   - The 

pc_decrypt

 module in app/ui/tool/pc_decrypt.py handles this

2. **Database Connection**: After decryption, the system connects to the databases

3. **Message Extraction**: The core message reading functionality is in 

msg.py

 and 

package_msg.py

:
   - 

get_messages_all()

: Retrieves all messages
   - 

get_messages()

: Retrieves messages for a specific user/chat
   - 

get_messages_by_days()

: Groups messages by date
   - 

get_messages_by_keyword()

: Searches messages containing keywords

4. **Message Processing**: 
   - The `PackageMsg` class in 

package_msg.py

 handles processing the raw data
   - For group chats, it parses the extra bytes to identify the actual sender using 

MessageBytesExtra


   - It maps senders to their contact information for display

5. **Contact Information**:
   - The project loads contact details from the MicroMsg database
   - It maps these to messages to display names and other user information

## Key Data Processing Functions

1. **Message parsing**: 
   - 

parser_chatroom_message()

 handles parsing group chat messages
   - Uses protobuf to decode additional message data from binary formats

2. **Data analysis**:
   - Functions for message statistics: 

get_messages_by_hour()

, 

get_messages_by_days()

, etc.
   - Message search via keywords: 

get_messages_by_keyword()


   - Most chatted contacts: 

get_chatted_top_contacts()



3. **File handling**:
   - Media messages are linked to files in the WeChat directory
   - Message types include text (1), images (3), voice (34), video (43), and various other types

## UI Display

After extracting the data, the application presents it through a PyQt5-based interface, showing conversations, contacts, and providing analysis features through the main view component.

The process from database decryption to displaying messages ensures users can view their WeChat history independently of the WeChat application.