// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Voting {
    struct Election {
        string title;
        string[] candidates;
        mapping(uint256 => uint256) votes;
        bool exists;
    }

    mapping(uint256 => Election) private elections;
    uint256 public electionCount;

    mapping(uint256 => mapping(address => bool)) private hasVoted;

    event ElectionCreated(uint256 indexed electionId, string title);
    event VoteRecorded(uint256 indexed electionId, uint256 indexed candidateIndex, address voter);

    function createElection(string memory title, string[] memory candidates) public {
        require(bytes(title).length > 0, "Election title required");
        require(candidates.length > 1, "At least two candidates required");

        uint256 electionId = electionCount;
        Election storage election = elections[electionId];
        election.title = title;
        election.exists = true;

        for (uint256 i = 0; i < candidates.length; i++) {
            election.candidates.push(candidates[i]);
        }

        electionCount += 1;
        emit ElectionCreated(electionId, title);
    }

    function vote(uint256 electionId, uint256 candidateIndex) public {
        require(elections[electionId].exists, "Election does not exist");
        require(candidateIndex < elections[electionId].candidates.length, "Invalid candidate");
        require(!hasVoted[electionId][msg.sender], "Already voted");

        hasVoted[electionId][msg.sender] = true;
        elections[electionId].votes[candidateIndex] += 1;
        emit VoteRecorded(electionId, candidateIndex, msg.sender);
    }

    function getResults(uint256 electionId)
        public
        view
        returns (string[] memory, uint256[] memory)
    {
        require(elections[electionId].exists, "Election does not exist");

        Election storage election = elections[electionId];
        uint256 candidatesLength = election.candidates.length;
        uint256[] memory results = new uint256[](candidatesLength);

        for (uint256 i = 0; i < candidatesLength; i++) {
            results[i] = election.votes[i];
        }
        return (election.candidates, results);
    }
}
