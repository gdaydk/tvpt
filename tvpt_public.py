import os

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import pprint
from time import sleep
import http.client
import ast
import uuid

# initialise permissions
scopes = ["https://www.googleapis.com/auth/youtube.force-ssl"]

# to display data
pp = pprint.PrettyPrinter(indent=4)

# Disable OAuthlib's HTTPS verification and relax token scope when running locally.
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# CONNECT TO YOUTUBE DATA API
api_service_name_data = "youtube"
api_version_data = "v3"
client_secrets_file_data =  # Add client secrets file here

# Get credentials and create an API client
flow_data = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
    client_secrets_file_data, scopes)
credentials_data = flow_data.run_console()
youtube = googleapiclient.discovery.build(
    api_service_name_data, api_version_data, credentials=credentials_data)

# Initialising global variables
yt_video_id =  # Youtube video id (at the end of the YouTube video link)
default_tree_cost_aud = 0.46


# Main function
def main():

    # Check the view count and calculate the number of trees that should already be planted and use that as the last tree count

    starting_viewcount = yt_view_counter()
    last_tree_count = int(starting_viewcount / 250)

    # Print the tree count to console
    print("Last tree count is " + str(last_tree_count))

    while(True):

        try:
            total_viewcount = yt_view_counter()

            # Divide the total viewcount by 250 and store the rounded-down integer result as current_tree_count (1 tree per 250 views)
            current_tree_count = int(total_viewcount / 250)

            # If current_tree_count is larger than last_tree_count, calculate the difference and store it as new_trees
            if (current_tree_count > last_tree_count):
                new_trees = current_tree_count - last_tree_count
                last_tree_count = current_tree_count
                request_uuid = uuid.uuid4()

                # Purchase the new trees with Ecologi, passing a v4 uuid as the idempotency key
                buy_trees(new_trees, str(request_uuid))

                # Update the YouTube description with the number of trees planted
                update_yt_desc(current_tree_count)

                # Print the tree count to console
                print("Current tree count is " + str(current_tree_count))

            # If difference is a negative number, print to console, but continue running
            elif (current_tree_count < last_tree_count):
                tree_surplus = last_tree_count - current_tree_count
                print("Error. Current tree count is " + str(current_tree_count) + " and the last tree count was " +
                      str(last_tree_count) + ". It looks like we've purchased " + str(tree_surplus) + " too many trees. Program will continue running, consider checking this if the discrepancy is large.")

            else:
                print("No new trees yet.")

        except Exception as e:
            print("Error in main function: " + str(e))

        sleep(10*60)


def yt_view_counter():
    # Returns the view count for yt_video_id
    try:
        # request from youtube data api
        request_data = youtube.videos().list(
            part="snippet,statistics",
            id=yt_video_id
        )

        response_data = request_data.execute()

        # Store the data in variables to perform operations on
        data = response_data["items"][0]
        view_count = int(data["statistics"]["viewCount"])

        return view_count

    except Exception as e:
        print("Error counting views: " + str(e))


def buy_trees(new_trees, idempotency_key):
    # Plants trees, accepting a number of new trees and an idempotency key as arguments
    try:

        conn = http.client.HTTPSConnection("public.ecologi.com")

        payload = ("{\n  \"number\": " + str(new_trees) +
                   ",\n  \"name\": \"You, the beautiful viewers\"\n}")

        headers = {
            'Content-Type': "application/json",
            'Idempotency-Key': str(idempotency_key),
            'Authorization':  # Auth code for Ecologi API
        }

        conn.request("POST", "/impact/trees", payload, headers)

        res = conn.getresponse()
        ecologi_data = res.read()
        decoded_data = ecologi_data.decode("utf-8")
        decoded_data_dictionary = ast.literal_eval(decoded_data)

        print("Successfully purchased " + str(new_trees) + " new trees.")

        # Check the tree cost, if it has gone up, notify via console.
        total_tree_cost_aud = decoded_data_dictionary["amount"]
        if ((total_tree_cost_aud / new_trees) > default_tree_cost_aud):
            new_tree_cost = total_tree_cost_aud / new_trees

            print("Tree cost has increased. The new tree cost is " +
                  str(new_tree_cost))

    except Exception as e:
        print("Error purchasing trees, has this idempotency key been used before?: Exception:" + str(e))


def ecologi_tree_count():
   # Gets the total number of trees planted in the Ecologi forest so-far

    try:
        conn = http.client.HTTPSConnection("public.ecologi.com")

        headers = {'Content-Type': "application/json"}

        conn.request("GET", "/users/username/trees", headers=headers)

        res = conn.getresponse()
        data = res.read()
        decoded_data = data.decode("utf-8")
        decoded_data_dictionary = ast.literal_eval(decoded_data)

        e_tree_count = decoded_data_dictionary["total"]

        return e_tree_count

    except Exception as e:
        print("Error getting tree count from Ecologi: " + str(e))


def update_yt_desc(current_tree_count):
    # Updates the description for yt_video_id, accepting the tree count as an argument
    try:
        # request from youtube data api
        request_data = youtube.videos().list(
            part="snippet,statistics",
            id=yt_video_id
        )

        response_data = request_data.execute()

        # Store the data in variables to perform operations on
        data = response_data["items"][0]

        vid_snippet = data["snippet"]
        description = vid_snippet["description"]

        desc_update = """.
Trees planted by views: """ + str(current_tree_count) + """
Total trees planted: """ + str(ecologi_tree_count()) + """
See our Ecologi forest at https://ecologi.com/username
________________________________

Watch nang's videos about the YouTube API:
Part 1: https://www.youtube.com/watch?v=X4xtZv5nFIk
Part 2: https://www.youtube.com/watch?v=SxOgJKg-eZg

"""

        vid_snippet["description"] = desc_update

        request = youtube.videos().update(
            part="snippet",
            body={
                "id": yt_video_id,
                "snippet": vid_snippet
            }
        )
        response = request.execute()
        print("Updated video description")

    except Exception as e:
        print("Error updating description. Response from api: " +
              str(response) + " Exception: " + str(e))


# This is what kicks the whole thing off
if __name__ == "__main__":
    main()
