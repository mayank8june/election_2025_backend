from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import os
from supabase import create_client, Client

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Supabase Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Routes
@app.route('/api/posts', methods=['GET'])
def get_posts():
    """Fetch all posts, sorted by timestamp (newest first)."""
    try:
        response = supabase.table('posts').select('*').order('timestamp', desc=True).execute()
        if response.error:
            return jsonify({'message': response.error.message}), 500

        posts = response.data
        return jsonify(posts), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/posts', methods=['POST'])
def create_post():
    """Create a new post."""
    try:
        data = request.json
        content = data.get('content')
        if not content:
            return jsonify({'message': 'Content is required'}), 400

        response = supabase.table('posts').insert({
            'content': content,
            'votes': 0,
            'timestamp': 'now()'  # Use server timestamp
        }).execute()

        if response.error:
            return jsonify({'message': response.error.message}), 400

        return jsonify(response.data[0]), 201
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/posts/<int:post_id>/vote', methods=['POST'])
def vote_post(post_id):
    """Vote on a post (upvote or downvote)."""
    try:
        data = request.json
        user_id = data.get('userId')
        vote_type = data.get('voteType')  # 1 for upvote, -1 for downvote

        if not user_id or vote_type not in [-1, 1]:
            return jsonify({'message': 'Invalid vote request'}), 400

        # Fetch the post
        response = supabase.table('posts').select('*').eq('id', post_id).execute()
        if response.error or len(response.data) == 0:
            return jsonify({'message': 'Post not found'}), 404

        post = response.data[0]

        # Get the voters array and votes count
        voters = post.get('voters', [])
        current_votes = post.get('votes', 0)

        # Check if the user has already voted
        existing_vote = next((v for v in voters if v['userId'] == user_id), None)

        if existing_vote:
            if existing_vote['voteType'] == vote_type:
                # Remove vote if clicking the same button
                current_votes -= vote_type
                voters = [v for v in voters if v['userId'] != user_id]
            else:
                # Change vote direction
                current_votes += (vote_type * 2)
                for v in voters:
                    if v['userId'] == user_id:
                        v['voteType'] = vote_type
        else:
            # Add new vote
            current_votes += vote_type
            voters.append({'userId': user_id, 'voteType': vote_type})

        # Update the post in Supabase
        update_response = supabase.table('posts').update({
            'votes': current_votes,
            'voters': voters
        }).eq('id', post_id).execute()

        if update_response.error:
            return jsonify({'message': update_response.error.message}), 400

        return jsonify(update_response.data[0]), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.getenv('PORT', 5000), debug=True)
