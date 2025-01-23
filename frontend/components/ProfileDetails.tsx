"use client";

import { Card, CardContent } from "@/components/ui/card";
import { User } from "lucide-react";

interface ProfileData {
  emailAddress: string;
  displayName: string;
  status: string;
  profileData?: {
    emailAddress: string;
    messagesTotal?: number;
    threadsTotal?: number;
    historyId?: string;
  };
}

interface ProfileDetailsProps {
  profile: ProfileData;
}

export function ProfileDetails({ profile }: ProfileDetailsProps) {
  return (
    <Card>
      <CardContent className="pt-6">
        {/* Profile Info */}
        <div className="flex items-center gap-4 mb-6">
          <div className="p-2 rounded-full bg-gray-100">
            <User className="h-5 w-5" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h3 className="font-medium">{profile.displayName}</h3>
              <span className="text-sm text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
                {profile.status}
              </span>
            </div>
            <p className="text-sm text-muted-foreground">{profile.emailAddress}</p>
          </div>
        </div>

        {/* Stats */}
        {profile.profileData && (
          <div className="grid grid-cols-2 gap-4">
            <div className="border rounded p-3">
              <div className="text-sm text-muted-foreground">Messages</div>
              <div className="text-xl font-semibold mt-1">
                {profile.profileData.messagesTotal?.toLocaleString()}
              </div>
            </div>
            <div className="border rounded p-3">
              <div className="text-sm text-muted-foreground">Threads</div>
              <div className="text-xl font-semibold mt-1">
                {profile.profileData.threadsTotal?.toLocaleString()}
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
} 