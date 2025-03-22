from flask import Flask, request, jsonify
from flask_cors import CORS
import math
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global state storage (could be replaced with a database in production)
exercise_states = {}

@app.route('/process_landmarks', methods=['POST'])
def process_landmarks():
    """Process landmarks from the frontend and return exercise data"""
    try:
        data = request.json
        landmarks = data.get('landmarks', [])
        exercise_type = data.get('exerciseType', 'bicepCurl')
        
        # Get client ID (in production, you'd use a proper authentication system)
        client_id = request.remote_addr
        
        # Initialize state for this client if not exists
        if client_id not in exercise_states:
            exercise_states[client_id] = {
                'repCounter': 0,
                'stage': 'down',
                'lastRepTime': 0,
                'holdStart': 0,
                'leftArmStage': 'down',
                'rightArmStage': 'down',
                'leftArmHoldStart': 0,
                'rightArmHoldStart': 0
            }
        
        client_state = exercise_states[client_id]
        current_time = int(time.time() * 1000)  # Current time in milliseconds
        rep_cooldown = 1000  # Prevent double counting
        hold_threshold = 500  # Time to hold at position
        
        # Process landmarks based on exercise type
        result = {
            'repCounter': client_state['repCounter'],
            'stage': client_state['stage'],
            'feedback': ''
        }
        
        # Process different exercise types
        if exercise_type == 'bicepCurl':
            result = process_bicep_curl(landmarks, client_state, current_time, rep_cooldown, hold_threshold)
        elif exercise_type == 'squat':
            result = process_squat(landmarks, client_state, current_time, rep_cooldown, hold_threshold)
        elif exercise_type == 'pushup':
            result = process_pushup(landmarks, client_state, current_time, rep_cooldown, hold_threshold)
        elif exercise_type == 'shoulderPress':
            result = process_shoulder_press(landmarks, client_state, current_time, rep_cooldown, hold_threshold)
        elif exercise_type == 'handstand':
            result = process_handstand(landmarks, client_state, current_time, rep_cooldown, hold_threshold)
        elif exercise_type == 'pullUp':
            result = process_pull_up(landmarks, client_state, current_time, rep_cooldown)
        elif exercise_type == 'situp':
            result = process_situp(landmarks, client_state, current_time, rep_cooldown, hold_threshold)
        elif exercise_type == 'jumpingJacks':
            result = process_jumping_jacks(landmarks, client_state, current_time, rep_cooldown, hold_threshold)
        elif exercise_type == 'lunge':
            result = process_lunge(landmarks, client_state, current_time, rep_cooldown, hold_threshold)
        
        # Update client state with the new values
        exercise_states[client_id] = client_state
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Error processing landmarks: {str(e)}")
        return jsonify({'error': str(e)}), 500


def calculate_angle(a, b, c):
    """Calculate angle between three points"""
    try:
        # Convert to vector from pointB to pointA and pointB to pointC
        vector_ba = {
            'x': a['x'] - b['x'],
            'y': a['y'] - b['y']
        }

        vector_bc = {
            'x': c['x'] - b['x'],
            'y': c['y'] - b['y']
        }

        # Calculate dot product
        dot_product = vector_ba['x'] * vector_bc['x'] + vector_ba['y'] * vector_bc['y']

        # Calculate magnitudes
        magnitude_ba = math.sqrt(vector_ba['x']**2 + vector_ba['y']**2)
        magnitude_bc = math.sqrt(vector_bc['x']**2 + vector_bc['y']**2)

        # Calculate angle in radians (handle division by zero or invalid inputs)
        if magnitude_ba == 0 or magnitude_bc == 0:
            return 0
            
        cos_angle = dot_product / (magnitude_ba * magnitude_bc)
        
        # Handle floating point errors that could make cos_angle outside [-1, 1]
        cos_angle = max(min(cos_angle, 1.0), -1.0)
        
        angle_rad = math.acos(cos_angle)

        # Convert to degrees
        angle_deg = angle_rad * (180 / math.pi)
        
        return angle_deg
    
    except Exception as e:
        print(f"Error calculating angle: {str(e)}")
        return 0


def process_bicep_curl(landmarks, state, current_time, rep_cooldown, hold_threshold):
    """Process landmarks for bicep curl exercise"""
    try:
        # Left arm
        left_shoulder = landmarks[11]
        left_elbow = landmarks[13]
        left_wrist = landmarks[15]

        # Right arm
        right_shoulder = landmarks[12]
        right_elbow = landmarks[14]
        right_wrist = landmarks[16]

        # Track state for both arms
        left_angle = None
        right_angle = None
        left_curl_detected = False
        right_curl_detected = False
        angles = {}

        # Calculate and store left arm angle
        if all(k in left_shoulder for k in ['x', 'y']) and all(k in left_elbow for k in ['x', 'y']) and all(k in left_wrist for k in ['x', 'y']):
            left_angle = calculate_angle(left_shoulder, left_elbow, left_wrist)
            angles['L'] = left_angle

            # Detect left arm curl
            if left_angle > 150:
                state['leftArmStage'] = "down"
                state['leftArmHoldStart'] = current_time
            if left_angle < 40 and state['leftArmStage'] == "down":
                if current_time - state['leftArmHoldStart'] > hold_threshold:
                    left_curl_detected = True
                    state['leftArmStage'] = "up"

        # Calculate and store right arm angle
        if all(k in right_shoulder for k in ['x', 'y']) and all(k in right_elbow for k in ['x', 'y']) and all(k in right_wrist for k in ['x', 'y']):
            right_angle = calculate_angle(right_shoulder, right_elbow, right_wrist)
            angles['R'] = right_angle

            # Detect right arm curl
            if right_angle > 150:
                state['rightArmStage'] = "down"
                state['rightArmHoldStart'] = current_time
            if right_angle < 40 and state['rightArmStage'] == "down":
                if current_time - state['rightArmHoldStart'] > hold_threshold:
                    right_curl_detected = True
                    state['rightArmStage'] = "up"

        # Count rep if either arm completes a curl and enough time has passed since last rep
        if (left_curl_detected or right_curl_detected) and current_time - state['lastRepTime'] > rep_cooldown:
            state['repCounter'] += 1
            state['lastRepTime'] = current_time
            
            # Generate feedback
            feedback = "Good rep!"
            if left_curl_detected and right_curl_detected:
                feedback = "Great form! Both arms curled."
            elif left_curl_detected:
                feedback = "Left arm curl detected."
            elif right_curl_detected:
                feedback = "Right arm curl detected."

            return {
                'repCounter': state['repCounter'],
                'stage': 'up' if left_curl_detected or right_curl_detected else 'down',
                'feedback': feedback,
                'angles': angles
            }

        return {
            'repCounter': state['repCounter'],
            'stage': state['leftArmStage'] if left_curl_detected else state['rightArmStage'],
            'angles': angles
        }
        
    except Exception as e:
        print(f"Error in bicep curl detection: {str(e)}")
        return {
            'repCounter': state['repCounter'],
            'stage': state['stage'],
            'feedback': f"Error: {str(e)}"
        }


def process_squat(landmarks, state, current_time, rep_cooldown, hold_threshold):
    """Process landmarks for squat exercise"""
    try:
        # Get landmarks for both legs
        left_hip = landmarks[23]
        left_knee = landmarks[25]
        left_ankle = landmarks[27]
        right_hip = landmarks[24]
        right_knee = landmarks[26]
        right_ankle = landmarks[28]

        # Variables to store angles and status
        left_knee_angle = None
        right_knee_angle = None
        avg_knee_angle = None
        hip_height = None
        angles = {}

        # Calculate left knee angle if landmarks are visible
        if all(k in left_hip for k in ['x', 'y']) and all(k in left_knee for k in ['x', 'y']) and all(k in left_ankle for k in ['x', 'y']):
            left_knee_angle = calculate_angle(left_hip, left_knee, left_ankle)
            angles['L'] = left_knee_angle

        # Calculate right knee angle if landmarks are visible
        if all(k in right_hip for k in ['x', 'y']) and all(k in right_knee for k in ['x', 'y']) and all(k in right_ankle for k in ['x', 'y']):
            right_knee_angle = calculate_angle(right_hip, right_knee, right_ankle)
            angles['R'] = right_knee_angle

        # Calculate average knee angle if both are available
        if left_knee_angle is not None and right_knee_angle is not None:
            avg_knee_angle = (left_knee_angle + right_knee_angle) / 2
            angles['Avg'] = avg_knee_angle
        elif left_knee_angle is not None:
            avg_knee_angle = left_knee_angle
            angles['Avg'] = avg_knee_angle
        elif right_knee_angle is not None:
            avg_knee_angle = right_knee_angle
            angles['Avg'] = avg_knee_angle

        # Calculate hip height (normalized to image height)
        if all(k in left_hip for k in ['x', 'y']) and all(k in right_hip for k in ['x', 'y']):
            hip_height = (left_hip['y'] + right_hip['y']) / 2
            angles['HipHeight'] = hip_height * 100  # Convert to percentage

        # Process squat detection using both knee angles and hip height
        feedback = ""
        if avg_knee_angle is not None and hip_height is not None:
            # Standing position detection (straight legs and higher hip position)
            if avg_knee_angle > 160 and hip_height < 0.6:
                state['stage'] = "up"
                state['holdStart'] = current_time
                feedback = "Standing position detected"

            # Squat position detection (bent knees and lower hip position)
            if avg_knee_angle < 120 and hip_height > 0.65 and state['stage'] == "up":
                if current_time - state['holdStart'] > hold_threshold and current_time - state['lastRepTime'] > rep_cooldown:
                    state['stage'] = "down"
                    state['repCounter'] += 1
                    state['lastRepTime'] = current_time
                    feedback = "Rep complete! Good squat depth."
                else:
                    feedback = "Hold squat position"

            # Form feedback
            if state['stage'] == "down" and avg_knee_angle > 130:
                feedback = "Squat deeper for a better workout"
            elif state['stage'] == "up" and hip_height > 0.6:
                feedback = "Stand up straighter"

        return {
            'repCounter': state['repCounter'],
            'stage': state['stage'],
            'feedback': feedback,
            'angles': angles
        }
        
    except Exception as e:
        print(f"Error in squat detection: {str(e)}")
        return {
            'repCounter': state['repCounter'],
            'stage': state['stage'],
            'feedback': f"Error: {str(e)}"
        }


def process_pushup(landmarks, state, current_time, rep_cooldown, hold_threshold):
    """Process landmarks for pushup exercise"""
    try:
        # Get landmarks for both arms and shoulders
        left_shoulder = landmarks[11]
        left_elbow = landmarks[13]
        left_wrist = landmarks[15]
        right_shoulder = landmarks[12]
        right_elbow = landmarks[14]
        right_wrist = landmarks[16]

        # Additional body points for height/position tracking
        nose = landmarks[0]
        left_hip = landmarks[23]
        right_hip = landmarks[24]

        # Variables to store angles and status
        left_elbow_angle = None
        right_elbow_angle = None
        avg_elbow_angle = None
        body_height = None
        body_alignment = None
        angles = {}

        # Calculate left arm angle if landmarks are visible
        if all(k in left_shoulder for k in ['x', 'y']) and all(k in left_elbow for k in ['x', 'y']) and all(k in left_wrist for k in ['x', 'y']):
            left_elbow_angle = calculate_angle(left_shoulder, left_elbow, left_wrist)
            angles['L'] = left_elbow_angle

        # Calculate right arm angle if landmarks are visible
        if all(k in right_shoulder for k in ['x', 'y']) and all(k in right_elbow for k in ['x', 'y']) and all(k in right_wrist for k in ['x', 'y']):
            right_elbow_angle = calculate_angle(right_shoulder, right_elbow, right_wrist)
            angles['R'] = right_elbow_angle

        # Calculate average elbow angle if both are available
        if left_elbow_angle is not None and right_elbow_angle is not None:
            avg_elbow_angle = (left_elbow_angle + right_elbow_angle) / 2
            angles['Avg'] = avg_elbow_angle
        elif left_elbow_angle is not None:
            avg_elbow_angle = left_elbow_angle
            angles['Avg'] = avg_elbow_angle
        elif right_elbow_angle is not None:
            avg_elbow_angle = right_elbow_angle
            angles['Avg'] = avg_elbow_angle

        # Calculate body height (y-coordinate of shoulders)
        if all(k in left_shoulder for k in ['x', 'y']) and all(k in right_shoulder for k in ['x', 'y']):
            body_height = (left_shoulder['y'] + right_shoulder['y']) / 2
            angles['Height'] = body_height * 100  # Convert to percentage

        # Check body alignment (straight back)
        if (all(k in left_shoulder for k in ['x', 'y']) and all(k in right_shoulder for k in ['x', 'y']) and 
            all(k in left_hip for k in ['x', 'y']) and all(k in right_hip for k in ['x', 'y'])):
            
            shoulder_mid_x = (left_shoulder['x'] + right_shoulder['x']) / 2
            shoulder_mid_y = (left_shoulder['y'] + right_shoulder['y']) / 2
            hip_mid_x = (left_hip['x'] + right_hip['x']) / 2
            hip_mid_y = (left_hip['y'] + right_hip['y']) / 2

            # Calculate angle between shoulders and hips to check for body alignment
            alignment_angle = math.atan2(hip_mid_y - shoulder_mid_y, hip_mid_x - shoulder_mid_x) * 180 / math.pi
            alignment_angle = abs(alignment_angle)

            # Normalize to 0-90 degree range (0 = perfect horizontal alignment)
            if alignment_angle > 90:
                alignment_angle = 180 - alignment_angle

            body_alignment = alignment_angle
            angles['Align'] = body_alignment

        # Process pushup detection using elbow angles, body height, and alignment
        feedback = ""
        if avg_elbow_angle is not None and body_height is not None:
            # Up position detection (straight arms, higher body position)
            if avg_elbow_angle > 160 and body_height < 0.7:
                state['stage'] = "up"
                state['holdStart'] = current_time
                feedback = "Up position - good!"

            # Down position detection (bent arms, lower body position)
            if avg_elbow_angle < 90 and state['stage'] == "up":
                if current_time - state['holdStart'] > hold_threshold and current_time - state['lastRepTime'] > rep_cooldown:
                    state['stage'] = "down"
                    state['repCounter'] += 1
                    state['lastRepTime'] = current_time
                    feedback = "Rep complete! Good pushup."
                else:
                    feedback = "Down position - hold briefly"

            # Check and provide form feedback based on body alignment
            if body_alignment is not None and body_alignment > 15:
                feedback = "Keep your body straight!"

        return {
            'repCounter': state['repCounter'],
            'stage': state['stage'],
            'feedback': feedback,
            'angles': angles
        }
        
    except Exception as e:
        print(f"Error in pushup detection: {str(e)}")
        return {
            'repCounter': state['repCounter'],
            'stage': state['stage'],
            'feedback': f"Error: {str(e)}"
        }


def process_shoulder_press(landmarks, state, current_time, rep_cooldown, hold_threshold):
    """Process landmarks for shoulder press exercise"""
    try:
        # Get landmarks for both arms
        left_shoulder = landmarks[11]
        left_elbow = landmarks[13]
        left_wrist = landmarks[15]
        right_shoulder = landmarks[12]
        right_elbow = landmarks[14]
        right_wrist = landmarks[16]

        # Variables to store angles and positions
        left_elbow_angle = None
        right_elbow_angle = None
        left_wrist_above_shoulder = False
        right_wrist_above_shoulder = False
        angles = {}

        # Calculate left arm position and angle
        if all(k in left_shoulder for k in ['x', 'y']) and all(k in left_elbow for k in ['x', 'y']) and all(k in left_wrist for k in ['x', 'y']):
            left_elbow_angle = calculate_angle(left_wrist, left_elbow, left_shoulder)
            angles['L'] = left_elbow_angle

            # Check if left wrist is above shoulder
            left_wrist_above_shoulder = left_wrist['y'] < left_shoulder['y']
            angles['LWristPos'] = 1 if left_wrist_above_shoulder else 0

        # Calculate right arm position and angle
        if all(k in right_shoulder for k in ['x', 'y']) and all(k in right_elbow for k in ['x', 'y']) and all(k in right_wrist for k in ['x', 'y']):
            right_elbow_angle = calculate_angle(right_wrist, right_elbow, right_shoulder)
            angles['R'] = right_elbow_angle

            # Check if right wrist is above shoulder
            right_wrist_above_shoulder = right_wrist['y'] < right_shoulder['y']
            angles['RWristPos'] = 1 if right_wrist_above_shoulder else 0

        # Calculate average elbow angle if both are available
        avg_elbow_angle = None
        if left_elbow_angle is not None and right_elbow_angle is not None:
            avg_elbow_angle = (left_elbow_angle + right_elbow_angle) / 2
            angles['Avg'] = avg_elbow_angle
        elif left_elbow_angle is not None:
            avg_elbow_angle = left_elbow_angle
            angles['Avg'] = avg_elbow_angle
        elif right_elbow_angle is not None:
            avg_elbow_angle = right_elbow_angle
            angles['Avg'] = avg_elbow_angle

        # Determine arm positions for stage detection
        both_wrists_below_shoulder = not left_wrist_above_shoulder and not right_wrist_above_shoulder
        both_wrists_above_shoulder = left_wrist_above_shoulder and right_wrist_above_shoulder
        one_wrist_above_shoulder = left_wrist_above_shoulder or right_wrist_above_shoulder

        # Process shoulder press detection
        feedback = ""
        if avg_elbow_angle is not None:
            # Starting (down) position - arms bent, wrists below shoulders
            if avg_elbow_angle < 100 and both_wrists_below_shoulder:
                state['stage'] = "down"
                state['holdStart'] = current_time
                feedback = "Ready position - good start"

            # Up position - arms extended, wrists above shoulders
            if avg_elbow_angle > 140 and (both_wrists_above_shoulder or (one_wrist_above_shoulder and avg_elbow_angle > 150)):
                if state['stage'] == "down" and current_time - state['holdStart'] > hold_threshold and current_time - state['lastRepTime'] > rep_cooldown:
                    state['stage'] = "up"
                    state['repCounter'] += 1
                    state['lastRepTime'] = current_time
                    feedback = "Rep complete! Good press."
                elif state['stage'] == "up":
                    feedback = "Press complete - hold position"

            # Form feedback
            if state['stage'] == "down" and avg_elbow_angle < 65:
                feedback = "Start with arms higher"

            if one_wrist_above_shoulder and not both_wrists_above_shoulder and state['stage'] == "up":
                feedback = "Press both arms evenly"

        return {
            'repCounter': state['repCounter'],
            'stage': state['stage'],
            'feedback': feedback,
            'angles': angles
        }
        
    except Exception as e:
        print(f"Error in shoulder press detection: {str(e)}")
        return {
            'repCounter': state['repCounter'],
            'stage': state['stage'],
            'feedback': f"Error: {str(e)}"
        }


def process_handstand(landmarks, state, current_time, rep_cooldown, hold_threshold):
    """Process landmarks for handstand exercise"""
    try:
        # Get key landmarks
        left_wrist = landmarks[15]
        right_wrist = landmarks[16]
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        left_hip = landmarks[23]
        right_hip = landmarks[24]
        left_knee = landmarks[25]
        right_knee = landmarks[26]
        left_ankle = landmarks[27]
        right_ankle = landmarks[28]

        # Check if all required landmarks are detected
        required_landmarks = [left_wrist, right_wrist, left_shoulder, right_shoulder, 
                            left_hip, right_hip, left_knee, right_knee, 
                            left_ankle, right_ankle]
        
        if not all(lm and all(k in lm for k in ['x', 'y']) for lm in required_landmarks):
            return {
                'repCounter': state['repCounter'],
                'stage': state['stage'],
                'feedback': "Move to ensure full body is visible"
            }

        # Calculate angle between shoulder, hip, and knee (should be straight in a proper handstand)
        left_body_angle = calculate_angle(left_shoulder, left_hip, left_knee)
        right_body_angle = calculate_angle(right_shoulder, right_hip, right_knee)

        # Calculate angle between hip, knee, and ankle (should be straight in a proper handstand)
        left_leg_angle = calculate_angle(left_hip, left_knee, left_ankle)
        right_leg_angle = calculate_angle(right_hip, right_knee, right_ankle)

        # Check if wrists are below ankles (inverted position)
        avg_ankle_y = (left_ankle['y'] + right_ankle['y']) / 2
        avg_wrist_y = (left_wrist['y'] + right_wrist['y']) / 2
        is_inverted = avg_ankle_y < avg_wrist_y

        # Calculate distance between wrists (to check if hands are properly placed)
        wrist_distance = math.sqrt(
            (right_wrist['x'] - left_wrist['x'])**2 + 
            (right_wrist['y'] - left_wrist['y'])**2
        )

        # Calculate shoulder width for reference (to normalize wrist distance)
        shoulder_distance = math.sqrt(
            (right_shoulder['x'] - left_shoulder['x'])**2 + 
            (right_shoulder['y'] - left_shoulder['y'])**2
        )

        # Check if body is straight (angles close to 180 degrees)
        body_angle_threshold = 160  # Degrees, closer to 180 is straighter
        is_left_body_straight = abs(left_body_angle) > body_angle_threshold
        is_right_body_straight = abs(right_body_angle) > body_angle_threshold
        is_left_leg_straight = abs(left_leg_angle) > body_angle_threshold
        is_right_leg_straight = abs(right_leg_angle) > body_angle_threshold

        # Check if hands are properly placed (around shoulder width apart)
        wrist_distance_ratio = wrist_distance / shoulder_distance if shoulder_distance > 0 else 0
        is_hand_placement_good = 0.8 < wrist_distance_ratio < 1.5

        # Determine if handstand form is good
        is_good_form = (is_inverted and 
                       is_left_body_straight and is_right_body_straight and 
                       is_left_leg_straight and is_right_leg_straight and 
                       is_hand_placement_good)

        # Store angles for UI
        angles = {
            'LBody': left_body_angle,
            'RBody': right_body_angle,
            'LLeg': left_leg_angle,
            'RLeg': right_leg_angle,
            'WristRatio': wrist_distance_ratio
        }

        # Generate feedback based on form
        feedback = ""
        if not is_inverted:
            feedback = "Get into inverted position"
        elif not (is_left_body_straight and is_right_body_straight):
            feedback = "Keep your body straight"
        elif not (is_left_leg_straight and is_right_leg_straight):
            feedback = "Straighten your legs"
        elif not is_hand_placement_good:
            if wrist_distance_ratio < 0.8:
                feedback = "Place hands wider apart"
            else:
                feedback = "Place hands closer together"
        elif is_good_form:
            feedback = "Great handstand form!"

        # If in a good handstand position, track the hold time
        if is_good_form:
            if state['stage'] != "inverted":
                state['holdStart'] = current_time
                state['stage'] = "inverted"
                feedback = "Good handstand position - hold it!"

            # If held long enough, count as a rep
            if current_time - state['holdStart'] > hold_threshold and state['stage'] == "inverted":
                if current_time - state['lastRepTime'] > rep_cooldown:
                    state['repCounter'] += 1
                    state['lastRepTime'] = current_time
                    feedback = "Handstand held! Great job!"
        else:
            # Reset if form breaks during a hold
            if state['stage'] == "inverted":
                state['stage'] = "normal"

        return {
            'repCounter': state['repCounter'],
            'stage': state['stage'],
            'feedback': feedback,
            'angles': angles
        }
        
    except Exception as e:
        print(f"Error in handstand detection: {str(e)}")
        return {
            'repCounter': state['repCounter'],
            'stage': state['stage'],
            'feedback': f"Error: {str(e)}"
        }


def process_pull_up(landmarks, state, current_time, rep_cooldown):
    """Process landmarks for pull-up exercise"""
    try:
        # Get coordinates for both sides
        left_shoulder = landmarks[11]
        left_elbow = landmarks[13]
        left_wrist = landmarks[15]
        right_shoulder = landmarks[12]
        right_elbow = landmarks[14]
        right_wrist = landmarks[16]

        # Check if we have valid landmarks for at least one side
        left_valid = (left_shoulder and left_elbow and left_wrist and
                     all(k in left_shoulder for k in ['x', 'y']) and
                     all(k in left_elbow for k in ['x', 'y']) and
                     all(k in left_wrist for k in ['x', 'y']))
        
        right_valid = (right_shoulder and right_elbow and right_wrist and
                      all(k in right_shoulder for k in ['x', 'y']) and
                      all(k in right_elbow for k in ['x', 'y']) and
                      all(k in right_wrist for k in ['x', 'y']))

        if not left_valid and not right_valid:
            return {
                'repCounter': state['repCounter'],
                'stage': state['stage'],
                'feedback': "Position not clear - adjust camera"
            }

        # Calculate angles for both sides
        left_angle = None
        right_angle = None
        angles = {}

        if left_valid:
            left_angle = calculate_angle(
                {'x': left_shoulder['x'], 'y': left_shoulder['y']},
                {'x': left_elbow['x'], 'y': left_elbow['y']},
                {'x': left_wrist['x'], 'y': left_wrist['y']}
            )
            angles['L'] = left_angle

        if right_valid:
            right_angle = calculate_angle(
                {'x': right_shoulder['x'], 'y': right_shoulder['y']},
                {'x': right_elbow['x'], 'y': right_elbow['y']},
                {'x': right_wrist['x'], 'y': right_wrist['y']}
            )
            angles['R'] = right_angle

        # Average the angles if both sides are valid, otherwise use the valid one
        arm_angle = None
        if left_valid and right_valid:
            arm_angle = (left_angle + right_angle) / 2
            angles['Avg'] = arm_angle
        elif left_valid:
            arm_angle = left_angle
            angles['Avg'] = arm_angle
        else:
            arm_angle = right_angle
            angles['Avg'] = arm_angle

        # Store the previous stage to detect transitions
        previous_stage = state['stage']

        # Determine pull-up stage based on arm angle
        # For pull-ups, when arms are bent (small angle) we're in "up" position
        if arm_angle < 50:
            state['stage'] = "up"
        elif arm_angle > 150:
            state['stage'] = "down"

        # Generate feedback based on stage
        feedback = ""
        if state['stage'] == "up":
            feedback = "Up position - good!"
        elif state['stage'] == "down":
            feedback = "Down position - pull up!"

        # Count rep when transitioning from "up" to "down" with cooldown
        if previous_stage == "up" and state['stage'] == "down" and current_time - state['lastRepTime'] > rep_cooldown:
            state['repCounter'] += 1
            state['lastRepTime'] = current_time
            feedback = "Rep complete! Good pull-up."

        return {
            'repCounter': state['repCounter'],
            'stage': state['stage'],
            'feedback': feedback,
            'angles': angles
        }
        
    except Exception as e:
        print(f"Error in pull-up detection: {str(e)}")
        return {
            'repCounter': state['repCounter'],
            'stage': state['stage'],
            'feedback': f"Error: {str(e)}"
        }


def process_situp(landmarks, state, current_time, rep_cooldown, hold_threshold):
    """Process landmarks for sit-up exercise"""
    try:
        # Get landmarks for both sides
        left_shoulder = landmarks[11]
        left_hip = landmarks[23]
        left_knee = landmarks[25]
        right_shoulder = landmarks[12]
        right_hip = landmarks[24]
        right_knee = landmarks[26]

        # Initialize variables to track angles
        left_angle = 0
        right_angle = 0
        avg_angle = 0
        angles = {}

        # Check if we have all required landmarks
        if (left_shoulder and left_hip and left_knee and right_shoulder and right_hip and right_knee and
            all(k in left_shoulder for k in ['x', 'y']) and all(k in left_hip for k in ['x', 'y']) and 
            all(k in left_knee for k in ['x', 'y']) and all(k in right_shoulder for k in ['x', 'y']) and 
            all(k in right_hip for k in ['x', 'y']) and all(k in right_knee for k in ['x', 'y'])):

            # Calculate angle for left side
            left_angle = calculate_angle(
                {'x': left_shoulder['x'], 'y': left_shoulder['y']},
                {'x': left_hip['x'], 'y': left_hip['y']},
                {'x': left_knee['x'], 'y': left_knee['y']}
            )
            angles['L'] = left_angle

            # Calculate angle for right side
            right_angle = calculate_angle(
                {'x': right_shoulder['x'], 'y': right_shoulder['y']},
                {'x': right_hip['x'], 'y': right_hip['y']},
                {'x': right_knee['x'], 'y': right_knee['y']}
            )
            angles['R'] = right_angle

            # Calculate average angle (for more stability)
            avg_angle = (left_angle + right_angle) / 2
            angles['Avg'] = avg_angle

            # Rep counting logic using average angle for more stability
            feedback = ""
            if avg_angle > 160:
                # Lying flat
                state['stage'] = "down"
                state['holdStart'] = current_time
                feedback = "Down position - prepare to sit up"

            if avg_angle < 80 and state['stage'] == "down":
                # Sitting up
                if current_time - state['holdStart'] > hold_threshold and current_time - state['lastRepTime'] > rep_cooldown:
                    state['stage'] = "up"
                    state['repCounter'] += 1
                    state['lastRepTime'] = current_time
                    feedback = "Rep complete! Good sit-up."
                else:
                    feedback = "Almost there - complete the sit-up"

            return {
                'repCounter': state['repCounter'],
                'stage': state['stage'],
                'feedback': feedback,
                'angles': angles
            }
        else:
            return {
                'repCounter': state['repCounter'],
                'stage': state['stage'],
                'feedback': "Position not clear - adjust camera",
                'angles': {}
            }
        
    except Exception as e:
        print(f"Error in sit-up detection: {str(e)}")
        return {
            'repCounter': state['repCounter'],
            'stage': state['stage'],
            'feedback': f"Error: {str(e)}"
        }


def process_jumping_jacks(landmarks, state, current_time, rep_cooldown, hold_threshold):
    """Process landmarks for jumping jacks exercise"""
    try:
        # Extract key landmarks
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        left_elbow = landmarks[13]
        right_elbow = landmarks[14]
        left_wrist = landmarks[15]
        right_wrist = landmarks[16]
        left_hip = landmarks[23]
        right_hip = landmarks[24]
        left_knee = landmarks[25]
        right_knee = landmarks[26]
        left_ankle = landmarks[27]
        right_ankle = landmarks[28]

        # Check if all landmarks are present and have x, y coordinates
        key_points = [
            left_shoulder, right_shoulder, left_elbow, right_elbow, left_wrist, right_wrist,
            left_hip, right_hip, left_knee, right_knee, left_ankle, right_ankle
        ]
        
        if not all(point and all(k in point for k in ['x', 'y']) for point in key_points):
            return {
                'repCounter': state['repCounter'],
                'stage': state['stage'],
                'feedback': "Position not clear - adjust camera",
                'angles': {}
            }

        # Calculate arm angles (angle between shoulder-elbow-wrist)
        left_arm_angle = calculate_angle(left_shoulder, left_elbow, left_wrist)
        right_arm_angle = calculate_angle(right_shoulder, right_elbow, right_wrist)

        # Calculate shoulder angles (angle between hip-shoulder-elbow)
        left_shoulder_angle = calculate_angle(left_hip, left_shoulder, left_elbow)
        right_shoulder_angle = calculate_angle(right_hip, right_shoulder, right_elbow)

        # Calculate leg angles (angle between hip-knee-ankle)
        left_leg_angle = calculate_angle(left_hip, left_knee, left_ankle)
        right_leg_angle = calculate_angle(right_hip, right_knee, right_ankle)

        # Calculate hip angles (angle between shoulder-hip-knee)
        left_hip_angle = calculate_angle(left_shoulder, left_hip, left_knee)
        right_hip_angle = calculate_angle(right_shoulder, right_hip, right_knee)

        # Store angles for display
        angles = {
            'LArm': left_arm_angle,
            'RArm': right_arm_angle,
            'LShoulder': left_shoulder_angle,
            'RShoulder': right_shoulder_angle,
            'LLeg': left_leg_angle,
            'RLeg': right_leg_angle,
            'LHip': left_hip_angle,
            'RHip': right_hip_angle
        }

        # Detect jumping jack phases using angles
        # Closed position: Arms down (large arm angle, small shoulder angle) and legs together (large leg angle, small hip angle)
        is_closed_position = (
            left_arm_angle > 150 and right_arm_angle > 150 and
            left_shoulder_angle < 50 and right_shoulder_angle < 50 and
            left_leg_angle > 160 and right_leg_angle > 160 and
            left_hip_angle < 30 and right_hip_angle < 30
        )

        # Open position: Arms up (small arm angle, large shoulder angle) and legs apart (small leg angle, large hip angle)
        is_open_position = (
            left_arm_angle < 120 and right_arm_angle < 120 and
            left_shoulder_angle > 160 and right_shoulder_angle > 160 and
            left_leg_angle < 140 and right_leg_angle < 140 and
            left_hip_angle > 50 and right_hip_angle > 50
        )

        feedback = ""
        if is_closed_position:
            state['stage'] = "closed"
            state['holdStart'] = current_time
            feedback = "Closed position - prepare to jump"

        if is_open_position and state['stage'] == "closed":
            if current_time - state['holdStart'] > hold_threshold and current_time - state['lastRepTime'] > rep_cooldown:
                state['stage'] = "open"
                state['repCounter'] += 1
                state['lastRepTime'] = current_time
                feedback = "Rep complete! Good jumping jack."
            else:
                feedback = "Open position - good form"
        
        if not is_open_position and not is_closed_position:
            feedback = "Transition - continue your movement"

        return {
            'repCounter': state['repCounter'],
            'stage': state['stage'],
            'feedback': feedback,
            'angles': angles
        }
        
    except Exception as e:
        print(f"Error in jumping jacks detection: {str(e)}")
        return {
            'repCounter': state['repCounter'],
            'stage': state['stage'],
            'feedback': f"Error: {str(e)}"
        }


def process_lunge(landmarks, state, current_time, rep_cooldown, hold_threshold):
    """Process landmarks for lunge exercise"""
    try:
        # Get landmarks for both sides of the body
        left_hip = landmarks[23]
        left_knee = landmarks[25]
        left_ankle = landmarks[27]
        right_hip = landmarks[24]
        right_knee = landmarks[26]
        right_ankle = landmarks[28]

        # Check if all landmarks are present with x, y coordinates
        if not all(
            point and all(k in point for k in ['x', 'y']) 
            for point in [left_hip, left_knee, left_ankle, right_hip, right_knee, right_ankle]
        ):
            return {
                'repCounter': state['repCounter'],
                'stage': state['stage'],
                'feedback': "Position not clear - adjust camera",
                'angles': {}
            }

        # Calculate leg angles for both sides
        left_leg_angle = calculate_angle(
            {'x': left_hip['x'], 'y': left_hip['y']},
            {'x': left_knee['x'], 'y': left_knee['y']},
            {'x': left_ankle['x'], 'y': left_ankle['y']}
        )

        right_leg_angle = calculate_angle(
            {'x': right_hip['x'], 'y': right_hip['y']},
            {'x': right_knee['x'], 'y': right_knee['y']},
            {'x': right_ankle['x'], 'y': right_ankle['y']}
        )

        # Calculate vertical distance between knees to detect lunge position
        knee_height_diff = abs(left_knee['y'] - right_knee['y'])

        # Determine which leg is in front (lower knee is the front leg)
        front_leg_angle = right_leg_angle if left_knee['y'] > right_knee['y'] else left_leg_angle
        back_leg_angle = left_leg_angle if left_knee['y'] > right_knee['y'] else right_leg_angle
        
        # Store angles for display
        angles = {
            'LLeg': left_leg_angle,
            'RLeg': right_leg_angle,
            'Front': front_leg_angle,
            'Back': back_leg_angle,
            'KneeDiff': knee_height_diff * 100  # Convert to percentage
        }

        # Track standing position - both legs relatively straight
        feedback = ""
        if (left_leg_angle > 150 and right_leg_angle > 150) and knee_height_diff < 0.1:
            state['stage'] = "up"
            state['holdStart'] = current_time
            feedback = "Standing position - prepare for lunge"

        # Proper lunge detection - front leg bent, back leg straighter, significant height difference
        proper_front_angle = front_leg_angle < 110  # Front knee should be bent (~90° is ideal)
        proper_back_angle = back_leg_angle > 130    # Back leg should be straighter
        proper_knee_height = knee_height_diff > 0.2  # Sufficient height difference between knees

        if proper_front_angle and proper_back_angle and proper_knee_height and state['stage'] == "up":
            if current_time - state['holdStart'] > hold_threshold and current_time - state['lastRepTime'] > rep_cooldown:
                state['stage'] = "down"
                state['repCounter'] += 1
                state['lastRepTime'] = current_time
                feedback = "Rep complete! Good lunge."
            else:
                feedback = "Lunge position - hold it"
        
        # Form feedback
        if state['stage'] == "down" and not proper_front_angle:
            feedback = "Bend your front knee more"
        elif state['stage'] == "down" and not proper_back_angle:
            feedback = "Keep your back leg straighter"
        elif state['stage'] == "up" and knee_height_diff > 0.1:
            feedback = "Stand with feet together"

        return {
            'repCounter': state['repCounter'],
            'stage': state['stage'],
            'feedback': feedback,
            'angles': angles
        }
        
    except Exception as e:
        print(f"Error in lunge detection: {str(e)}")
        return {
            'repCounter': state['repCounter'],
            'stage': state['stage'],
            'feedback': f"Error: {str(e)}"
        }


# Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))